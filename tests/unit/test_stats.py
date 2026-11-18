import pytest

from netspeed.measure import RequestResult, RunResult
from netspeed.stats import summarise


def _run(sizes_seconds, wall):
    reqs = tuple(
        RequestResult(index=i, status=200, bytes=b, seconds=s)
        for i, (b, s) in enumerate(sizes_seconds)
    )
    return RunResult(url="http://x", requests=reqs, wall_seconds=wall, parallel=1, keepalive=True)


def test_speed_uses_total_bytes_over_wall_clock_in_megabits():
    s = summarise(_run([(25_000_000, 2.0), (25_000_000, 2.0)], wall=4.0))
    assert s.count == 2
    assert s.total_bytes == 50_000_000
    assert s.total_mb == pytest.approx(50.0)
    assert s.avg_seconds == pytest.approx(2.0)
    assert s.mbps == pytest.approx(100.0)  # 50e6 B * 8 / 4 s / 1e6


def test_average_is_mean_of_request_durations_not_wall_clock():
    s = summarise(_run([(1_000_000, 1.0), (1_000_000, 3.0)], wall=3.0))  # overlapped
    assert s.avg_seconds == pytest.approx(2.0)
    assert s.mbps == pytest.approx(16 / 3)


def test_zero_wall_clock_is_rejected_rather_than_dividing_by_zero():
    with pytest.raises(ValueError):
        summarise(_run([(10, 0.0)], wall=0.0))


def test_empty_run_is_rejected():
    with pytest.raises(ValueError):
        summarise(_run([], wall=1.0))


def test_sub_second_runs_are_valid():
    assert summarise(_run([(1_000_000, 0.5)], wall=0.5)).mbps == pytest.approx(16.0)
