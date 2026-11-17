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
    stop = threading.Event()
    lock = threading.Lock()
    results: list[RequestResult] = []

    def record(result: RequestResult) -> None:
        with lock:
            results.append(result)
            if progress is not None:
                progress(result)

    def worker(indices: Iterable[int]) -> None:
        client = _make_client(timeout, transport) if keepalive else None
        try:
            for i in indices:
                if stop.is_set():
                    return
                if keepalive:
                    record(_fetch(client, url, i, clock))
                else:
                    with _make_client(timeout, transport) as fresh:
                        record(_fetch(fresh, url, i, clock))
        except httpx.HTTPError as exc:
            stop.set()
            raise MeasureError(f"request #{i + 1} failed: {exc}") from exc
        finally:
            if client is not None:
                client.close()

    slices = [range(w, count, workers) for w in range(workers)]
    run_start = clock()
    if workers == 1:
        worker(slices[0])
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in [pool.submit(worker, s) for s in slices]:
                future.result()
    run_end = clock()

    return RunResult(
        url=url,
        requests=tuple(sorted(results, key=lambda r: r.index)),
        wall_seconds=run_end - run_start,
        parallel=workers,
        keepalive=keepalive,
    )
