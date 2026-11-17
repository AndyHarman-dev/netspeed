import httpx
import pytest

from netspeed.measure import MeasureError, effective_parallel, run

from .test_measure import BODY, ok_transport, wire


def test_parallel_one_matches_sequential_shape():
    a = run("http://h/", count=5, transport=ok_transport())
    b = run("http://h/", count=5, transport=ok_transport(), parallel=1)
    assert [(r.index, r.bytes) for r in a.requests] == [(r.index, r.bytes) for r in b.requests]
    assert b.parallel == 1


def test_parallel_spreads_count_requests_and_sums_bytes():
    seen = []
    result = run("http://h/", count=10, parallel=4, transport=ok_transport(seen))
    assert len(seen) == 10
    assert [r.index for r in result.requests] == list(range(10))
    assert sum(r.bytes for r in result.requests) == 10 * len(BODY)
    assert result.parallel == 4


def test_parallel_requests_overlap_so_wall_clock_is_below_sum():
    result = run("http://h/", count=4, parallel=4, transport=ok_transport(delay=0.2))
    total = sum(r.seconds for r in result.requests)
    assert result.wall_seconds < total / 2


def test_parallel_failure_raises_and_reports_nothing():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return wire(500 if calls["n"] == 3 else 200, BODY)

    with pytest.raises(MeasureError):
        run("http://h/", count=10, parallel=2, transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(("count", "parallel", "expected"), [(10, 4, 4), (3, 8, 3), (1, 1, 1)])
def test_effective_parallel_is_clamped_to_count(count, parallel, expected):
    assert effective_parallel(count, parallel) == expected


def test_run_clamps_parallel_to_count():
    assert run("http://h/", count=2, parallel=8, transport=ok_transport()).parallel == 2
