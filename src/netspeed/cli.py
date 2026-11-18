"""Command-line entry point. Progress goes to stderr; the summary or JSON goes to stdout."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone

import httpx

from netspeed import __version__, measure
from netspeed.measure import MeasureError, RequestResult, RunResult
from netspeed.stats import Summary, summarise

DEFAULT_URL = "https://speed.cloudflare.com/__down?bytes=25000000"


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return value


def _http_url(text: str) -> str:
    try:
        url = httpx.URL(text)
    except httpx.InvalidURL as exc:
        raise argparse.ArgumentTypeError(f"invalid URL {text!r}: {exc}") from exc
    if url.scheme not in ("http", "https") or not url.host:
        raise argparse.ArgumentTypeError(f"not an http(s) URL: {text!r}")
    return text


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="netspeed",
        description="Download a URL repeatedly and report the download speed in Mbit/s.",
    )
    p.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        type=_http_url,
        help=f"file to download (default: {DEFAULT_URL})",
    )
    p.add_argument(
        "--count", type=_positive_int, default=10, help="number of requests (default: 10)"
    )
    p.add_argument(
        "--timeout",
        type=_positive_float,
        default=120.0,
        help="limit on each whole request in seconds (default: 120)",
    )
    p.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    p.add_argument(
        "--no-keepalive",
        dest="keepalive",
        action="store_false",
        help="open a new connection for every request",
    )
    p.add_argument(
        "--parallel",
        type=_positive_int,
        default=1,
        metavar="N",
        help="spread the requests over N concurrent connections (default: 1)",
    )
    p.add_argument("--version", action="version", version=f"netspeed {__version__}")
    return p


def _header(url: str, count: int, parallel: int, keepalive: bool) -> str:
    mode = "keep-alive" if keepalive else "new connection per request"
    spread = f" over {parallel} parallel connections" if parallel > 1 else ""
    return f"Knocking on {url} - {count} requests{spread}, {mode}"


def _progress_line(r: RequestResult) -> str:
    return f"  #{r.index + 1:<3} {r.seconds:7.3f} s  {r.bytes / 1e6:8.2f} MB"


def _text(s: Summary) -> str:
    return "\n".join(
        [
            f"Requests:          {s.count}",
            f"Average request:   {s.avg_seconds:.3f} s",
            f"Downloaded total:  {s.total_mb:.2f} MB",
            f"Download speed:    {s.mbps:.2f} Mbit/s",
        ]
    )


def _json(run: RunResult, s: Summary) -> str:
    return json.dumps(
        {
            "url": run.url,
            "count": s.count,
            "parallel": run.parallel,
            "keepalive": run.keepalive,
            "requests": [asdict(r) for r in run.requests],
            "total_bytes": s.total_bytes,
            "total_mb": s.total_mb,
            "avg_seconds": s.avg_seconds,
            "wall_seconds": s.wall_seconds,
            "mbps": s.mbps,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version": __version__,
        },
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    parallel = measure.effective_parallel(args.count, args.parallel)
    if parallel < args.parallel:
        print(
            f"warning: --parallel {args.parallel} exceeds --count {args.count}; using {parallel}",
            file=sys.stderr,
        )

    print(_header(args.url, args.count, parallel, args.keepalive), file=sys.stderr)
    try:
        run = measure.run(
            args.url,
            count=args.count,
            timeout=args.timeout,
            keepalive=args.keepalive,
            parallel=parallel,
            progress=lambda r: print(_progress_line(r), file=sys.stderr),
        )
    except MeasureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = summarise(run)
    print(_json(run, summary) if args.json else _text(summary))
    return 0
