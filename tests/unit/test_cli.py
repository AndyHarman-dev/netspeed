import json

import pytest

from netspeed import cli, measure
from netspeed.measure import MeasureError, RequestResult, RunResult


@pytest.fixture
def fake_run(monkeypatch):
    calls = {}

    def fake(url, count, timeout, keepalive, parallel, progress=None, **_):
        calls.update(url=url, count=count, timeout=timeout, keepalive=keepalive, parallel=parallel)
        reqs = tuple(RequestResult(i, 200, 25_000_000, 2.0) for i in range(count))
        for r in reqs:
            if progress:
                progress(r)
        return RunResult(
            url, reqs, wall_seconds=2.0 * count / parallel, parallel=parallel, keepalive=keepalive
        )

    monkeypatch.setattr(measure, "run", fake)
    return calls


def test_text_summary_on_stdout_progress_on_stderr(fake_run, capsys):
    assert cli.main(["http://h/big.jpg"]) == 0
    out, err = capsys.readouterr()
    assert "Requests:          10" in out
    assert "Average request:   2.000 s" in out
    assert "Downloaded total:  250.00 MB" in out
    assert "Download speed:    100.00 Mbit/s" in out
    assert "10 requests, keep-alive" in err
    assert "#10" in err
    out.encode("ascii")
    err.encode("ascii")


def test_defaults_are_ten_sequential_keepalive_requests_to_default_url(fake_run):
    cli.main([])
    assert fake_run == {
        "url": cli.DEFAULT_URL,
        "count": 10,
        "timeout": 30.0,
        "keepalive": True,
        "parallel": 1,
    }


def test_flags_are_passed_through(fake_run):
    cli.main(["http://h/", "--count", "4", "--timeout", "5", "--no-keepalive", "--parallel", "2"])
    assert fake_run == {
        "url": "http://h/",
        "count": 4,
        "timeout": 5.0,
        "keepalive": False,
        "parallel": 2,
    }


def test_parallel_header_names_connections(fake_run, capsys):
    cli.main(["http://h/", "--parallel", "4"])
    assert "10 requests over 4 parallel connections, keep-alive" in capsys.readouterr().err


def test_parallel_above_count_warns_and_clamps(fake_run, capsys):
    cli.main(["http://h/", "--count", "2", "--parallel", "8"])
    assert fake_run["parallel"] == 2
    assert "warning" in capsys.readouterr().err.lower()


def test_json_is_the_only_stdout(fake_run, capsys):
    assert cli.main(["http://h/", "--json", "--count", "2"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mbps"] == pytest.approx(100.0)
    assert data["count"] == 2
    assert data["total_bytes"] == 50_000_000
    assert data["parallel"] == 1 and data["keepalive"] is True
    assert len(data["requests"]) == 2 and data["requests"][0]["bytes"] == 25_000_000
    assert {"url", "avg_seconds", "wall_seconds", "total_mb", "timestamp", "version"} <= data.keys()


def test_measure_error_exits_1_with_message(monkeypatch, capsys):
    def boom(*a, **kw):
        raise MeasureError("request #3 failed: 404")

    monkeypatch.setattr(measure, "run", boom)
    assert cli.main(["http://h/"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "404" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["--count", "0"],
        ["--parallel", "0"],
        ["--timeout", "0"],
        ["ftp://h/x"],
        ["not a url"],
        ["http://h:abc/"],
    ],
)
def test_bad_arguments_exit_2(argv, fake_run):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2


def test_smallest_valid_values_are_accepted(fake_run):
    assert cli.main(["http://h/", "--count", "1", "--timeout", "0.5"]) == 0
    assert fake_run["count"] == 1 and fake_run["timeout"] == 0.5


def test_progress_line_shows_seconds_and_megabytes(fake_run, capsys):
    cli.main(["http://h/", "--count", "1"])
    assert "  #1     2.000 s     25.00 MB" in capsys.readouterr().err


def test_parallel_within_count_does_not_warn(fake_run, capsys):
    cli.main(["http://h/", "--count", "4", "--parallel", "4"])
    assert "warning" not in capsys.readouterr().err.lower()
