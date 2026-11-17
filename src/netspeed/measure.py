"""HTTP request loop: fetch a URL `count` times and time each full download."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

HEADERS = {"Cache-Control": "no-cache", "Accept-Encoding": "identity"}

Clock = Callable[[], float]


class MeasureError(Exception):
    """A request failed; the run produced no trustworthy speed."""


@dataclass(frozen=True)
class RequestResult:
    index: int
    status: int
    bytes: int
    seconds: float


@dataclass(frozen=True)
class RunResult:
    url: str
    requests: tuple[RequestResult, ...]
    wall_seconds: float
    parallel: int
    keepalive: bool


def effective_parallel(count: int, parallel: int) -> int:
    """Never run more workers than there are requests."""
    return min(count, parallel)


def _make_client(timeout: float, transport: httpx.BaseTransport | None) -> httpx.Client:
    return httpx.Client(timeout=timeout, transport=transport, follow_redirects=True)


def _cache_busted(url: str) -> httpx.URL:
    return httpx.URL(url).copy_merge_params({"_nocache": uuid.uuid4().hex})


def _fetch(client: httpx.Client, url: str, index: int, clock: Clock) -> RequestResult:
    t0 = clock()
    with client.stream("GET", _cache_busted(url), headers=HEADERS) as response:
        response.raise_for_status()
        size = sum(len(chunk) for chunk in response.iter_raw())
        status = response.status_code
    return RequestResult(index=index, status=status, bytes=size, seconds=clock() - t0)


@dataclass(frozen=True)
class _Job:
    """Everything a worker needs; shared read-only between workers."""

    url: str
    timeout: float
    keepalive: bool
    transport: httpx.BaseTransport | None
    clock: Clock
    record: Callable[[RequestResult], None]
    stop: threading.Event


def _fetch_once(job: _Job, shared: httpx.Client | None, index: int) -> RequestResult:
    if shared is not None:
        return _fetch(shared, job.url, index, job.clock)
    with _make_client(job.timeout, job.transport) as fresh:
        return _fetch(fresh, job.url, index, job.clock)


def _worker(job: _Job, indices: Iterable[int]) -> None:
    """Fetch `indices` one at a time on this worker's own client(s)."""
    shared = _make_client(job.timeout, job.transport) if job.keepalive else None
    try:
        for index in indices:
            if job.stop.is_set():
                return
            try:
                job.record(_fetch_once(job, shared, index))
            except httpx.HTTPError as exc:
                job.stop.set()
                raise MeasureError(f"request #{index + 1} failed: {exc}") from exc
    finally:
        if shared is not None:
            shared.close()


def _run_workers(job: _Job, slices: list[range]) -> None:
    with ThreadPoolExecutor(max_workers=len(slices)) as pool:
        for future in [pool.submit(_worker, job, s) for s in slices]:
            future.result()


def _recorder(
    results: list[RequestResult], progress: Callable[[RequestResult], None] | None
) -> Callable[[RequestResult], None]:
    lock = threading.Lock()

    def record(result: RequestResult) -> None:
        with lock:
            results.append(result)
            if progress is not None:
                progress(result)

    return record


def run(
    url: str,
    count: int = 10,
    timeout: float = 30.0,
    keepalive: bool = True,
    transport: httpx.BaseTransport | None = None,
    clock: Clock = time.perf_counter,
    parallel: int = 1,
    progress: Callable[[RequestResult], None] | None = None,
) -> RunResult:
    """Fetch `url` `count` times over `parallel` connections (1 = sequential).

    Each worker handles every N-th request index on its own client, one request at a
    time, so `parallel=1` is exactly the sequential loop. The first failure stops all
    workers and raises MeasureError; no partial result is returned.
    """
    workers = effective_parallel(count, parallel)
    results: list[RequestResult] = []
    job = _Job(
        url, timeout, keepalive, transport, clock, _recorder(results, progress), threading.Event()
    )

    run_start = clock()
    _run_workers(job, [range(w, count, workers) for w in range(workers)])
    run_end = clock()

    return RunResult(
        url=url,
        requests=tuple(sorted(results, key=lambda r: r.index)),
        wall_seconds=run_end - run_start,
        parallel=workers,
        keepalive=keepalive,
    )
