"""Pure maths over a RunResult. Units: MB = 10^6 bytes, Mbit/s = 10^6 bit/s."""

from __future__ import annotations

from dataclasses import dataclass

from netspeed.measure import RunResult


@dataclass(frozen=True)
class Summary:
    count: int
    total_bytes: int
    total_mb: float
    avg_seconds: float
    wall_seconds: float
    mbps: float


def summarise(run: RunResult) -> Summary:
    if not run.requests:
        raise ValueError("no requests to summarise")
    if run.wall_seconds <= 0:
        raise ValueError("wall-clock time must be positive")
    total = sum(r.bytes for r in run.requests)
    return Summary(
        count=len(run.requests),
        total_bytes=total,
        total_mb=total / 1e6,
        avg_seconds=sum(r.seconds for r in run.requests) / len(run.requests),
        wall_seconds=run.wall_seconds,
        mbps=total * 8 / run.wall_seconds / 1e6,
    )
