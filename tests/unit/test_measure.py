import inspect
import threading
import time

import httpx
import pytest

from netspeed import measure
from netspeed.measure import MeasureError, run

BODY = b"x" * 1000


def wire(status, body=b"", headers=None):
    """A response whose body is still a stream, like one arriving off the network."""
    return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers)


def ok_transport(seen=None, body=BODY, delay=0.0):
    lock = threading.Lock()

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            with lock:
                seen.append(request)
        if delay:
            time.sleep(delay)
        return wire(200, body)

    return httpx.MockTransport(handler)


def fake_clock(values):
    it = iter(values)
    return lambda: next(it)


def test_makes_count_requests_and_counts_body_bytes():
    seen = []
    result = run("http://h/f.jpg", count=10, transport=ok_transport(seen))
    assert len(seen) == 10
    assert [r.index for r in result.requests] == list(range(10))
    assert all(r.bytes == len(BODY) and r.status == 200 for r in result.requests)


def test_each_request_is_cache_busted_and_keeps_existing_query():
    seen = []
    run("http://h/__down?bytes=5", count=3, transport=ok_transport(seen))
    busters = {r.url.params["_nocache"] for r in seen}
    assert len(busters) == 3
    assert all(r.url.params["bytes"] == "5" for r in seen)
    assert all(r.headers["cache-control"] == "no-cache" for r in seen)
    assert all(r.headers["accept-encoding"] == "identity" for r in seen)


def test_counts_wire_bytes_not_decoded_bytes():
    import gzip

    raw = gzip.compress(b"a" * 100_000)

    def handler(request):
        return wire(200, raw, {"Content-Encoding": "gzip"})

    result = run("http://h/", count=1, transport=httpx.MockTransport(handler))
    assert result.requests[0].bytes == len(raw)


def test_timings_come_from_the_injected_clock():
    # run_start, (t0, t1) x 2, run_end
    clock = fake_clock([0.0, 0.0, 1.5, 1.5, 4.0, 4.0])
    result = run("http://h/", count=2, transport=ok_transport(), clock=clock)
    assert [r.seconds for r in result.requests] == [1.5, 2.5]
    assert result.wall_seconds == 4.0


def test_http_error_raises_measure_error():
    t = httpx.MockTransport(lambda r: httpx.Response(404))
    with pytest.raises(MeasureError, match=r"request #1 failed.*404"):
        run("http://h/", count=3, transport=t)


def test_transport_error_raises_measure_error():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(MeasureError, match="boom"):
        run("http://h/", count=1, transport=httpx.MockTransport(handler))


def test_follows_redirects():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "http://h/new"})
        return wire(200, BODY)

    result = run("http://h/old", count=1, transport=httpx.MockTransport(handler))
    assert result.requests[0].bytes == len(BODY)


@pytest.mark.parametrize(("keepalive", "clients"), [(True, 1), (False, 4)])
def test_keepalive_controls_client_reuse(monkeypatch, keepalive, clients):
    made = []
    real = measure._make_client

    def spy(*a, **kw):
        made.append(1)
        return real(*a, **kw)

    monkeypatch.setattr(measure, "_make_client", spy)
    run("http://h/", count=4, keepalive=keepalive, transport=ok_transport())
    assert len(made) == clients


def test_progress_callback_sees_every_request():
    got = []
    run("http://h/", count=3, transport=ok_transport(), progress=got.append)
    assert sorted(r.index for r in got) == [0, 1, 2]


def test_keepalive_is_the_default(monkeypatch):
    made = []
    real = measure._make_client
    monkeypatch.setattr(measure, "_make_client", lambda *a: made.append(1) or real(*a))
    result = run("http://h/", count=3, transport=ok_transport())
    assert len(made) == 1 and result.keepalive is True


class TrickleBody(httpx.SyncByteStream):
    """A body that keeps arriving: `chunks` small chunks, 50 ms apart."""

    def __init__(self, chunks):
        self.chunks = chunks

    def __iter__(self):
        for _ in range(self.chunks):
            time.sleep(0.05)
            yield b"x" * 100


def trickle_transport(chunks):
    return httpx.MockTransport(lambda request: httpx.Response(200, stream=TrickleBody(chunks)))


def test_timeout_caps_the_whole_request_not_each_read():
    # Every chunk arrives well inside the timeout; the download as a whole (2 s) does not.
    started = time.monotonic()
    with pytest.raises(MeasureError, match=r"request #1 failed: .*longer than 0.3 s"):
        run("http://h/", count=1, timeout=0.3, transport=trickle_transport(40))
    assert time.monotonic() - started < 1.0


def test_a_download_that_finishes_inside_the_timeout_succeeds():
    result = run("http://h/", count=1, timeout=1.0, transport=trickle_transport(4))
    assert result.requests[0].bytes == 400


def test_a_download_ending_exactly_at_the_deadline_succeeds():
    # The deadline timer reads 0 at the start and exactly `timeout` at the only chunk.
    ticks = iter([0.0, 1.0])
    result = run(
        "http://h/", count=1, timeout=1.0, transport=ok_transport(), timer=lambda: next(ticks)
    )
    assert result.requests[0].bytes == len(BODY)


def test_each_wait_for_data_has_its_own_fixed_limit_independent_of_timeout():
    client = measure._make_client(transport=None)
    assert client.timeout == httpx.Timeout(measure.WAIT_TIMEOUT)
    assert measure.WAIT_TIMEOUT == 30.0
    client.close()


def test_run_default_timeout_allows_slow_whole_downloads():
    assert inspect.signature(run).parameters["timeout"].default == 120.0
