# netspeed

A small cross-platform command-line tool that measures your download speed. It downloads a file over
HTTP several times, waits for each response to finish, then prints the average request time, the
total data downloaded, and the download speed.

```
$ netspeed https://speed.cloudflare.com/__down?bytes=25000000
Knocking on https://speed.cloudflare.com/__down?bytes=25000000 - 10 requests, keep-alive
  #1     6.512 s     25.00 MB
  ...
Requests:          10
Average request:   6.431 s
Downloaded total:  250.00 MB
Download speed:    31.09 Mbit/s
```

## Install

netspeed runs on Windows, macOS and Linux with Python 3.10 or newer. The easiest way to install it is
[uv](https://docs.astral.sh/uv/), which also downloads Python for you if you don't have it.

1. Install uv:
   - **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install netspeed:
   ```sh
   uv tool install git+https://github.com/AndyHarman-dev/netspeed.git
   ```
3. Open a new terminal and run `netspeed --version`.

To run it without installing: `uvx --from git+https://github.com/AndyHarman-dev/netspeed.git netspeed`.

## Usage

```
netspeed [URL] [--count N] [--timeout SEC] [--json] [--no-keepalive] [--parallel N] [--version]
```

| Option | Default | Meaning |
|---|---|---|
| `URL` | `https://speed.cloudflare.com/__down?bytes=25000000` | The file to download (http or https). A large file works best; a 25 MB or larger file gives stable numbers. |
| `--count N` | `10` | How many times to download it. |
| `--timeout SEC` | `30` | Per-request timeout. |
| `--json` | off | Print one JSON object (every request, totals, speed, timestamp) instead of text. |
| `--no-keepalive` | off | Open a new connection for every request, instead of reusing one. |
| `--parallel N` | `1` | Spread the requests over N connections at once. See [Parallel mode](#parallel-mode). |
| `--version` | | Print `netspeed X.Y.Z`. |

Progress lines go to stderr, and the summary or JSON goes to stdout, so `netspeed --json > result.json`
saves clean JSON. The exit code is `0` on success, `1` if a request fails, and `2` for invalid arguments.

## Units

| Value | Unit | Definition |
|---|---|---|
| Download speed | **Mbit/s** (megabits per second) | 10^6 bits per second, the same unit ISPs and most speed tests use. |
| Downloaded total | **MB** (megabytes) | 10^6 bytes. Note this is not MiB. |
| Average request | **s** (seconds) | The mean time of one request, from sending it to receiving its last byte. |

**Speed formula:**

```
speed (Mbit/s) = total bytes downloaded * 8 / wall-clock seconds / 1,000,000
```

The wall clock runs from the start of the first request to the end of the last one. In the default
sequential mode that equals the sum of the request times. Divide Mbit/s by 8 to get MB/s.

## How it measures

- **Sequential by default.** It makes the requests one after another and reads each response body
  fully before starting the next.
- **The full body is counted.** Bytes are counted as they arrive on the wire, with compression turned off
  (`Accept-Encoding: identity`), so the total is the real amount of data transferred.
- **No caching.** Each request gets a unique `_nocache=<random>` query parameter and a
  `Cache-Control: no-cache` header, so the file is not served from a cache.
- **One connection.** The same connection is reused across requests (keep-alive). `--no-keepalive` opens a
  new one each time, which also measures connection setup (DNS, TCP, TLS).
- **Errors stop the run.** Any failed request (HTTP error, timeout, connection drop) ends the run with exit
  code 1. netspeed reports no speed in that case, because a partial number would be misleading.

## Parallel mode

`--parallel N` runs the same `--count` requests over N connections at once. The speed is still total bytes
over wall-clock time. The average request time is still per request, so it grows as the connections share
the line.

It exists for comparisons with multi-connection speed tests (such as speedtest.net). On fast links one TCP
connection to one server often can't fill the line. A single stream then reads lower than such tests, and
`--parallel 4` closes most of that gap. The default sequential mode answers a different question: how
fast one download of this file is.

**Tip: pick a `--count` that N divides evenly**, such as `--count 12 --parallel 4`. The requests are dealt out to
the connections in turn, so the default 10 over 4 connections splits 3, 3, 2, 2. At the end of the run only
two connections are still downloading, and on a link that one connection can't fill, that tail pulls
the speed down. With 12, all four connections stay busy until the end.

## Limits

- The result measures the path to the server you chose. A far-away or slow server reads low even on a fast
  connection.
- Only download speed is measured, not upload or latency.

## Experiment: Wi-Fi vs LAN

A controlled comparison on a Windows laptop (Wi-Fi vs wired Ethernet, cross-checked against
speedtest.net) is in [`tests/experiment-lan-vs-wifi/`](tests/experiment-lan-vs-wifi/README.md).

## Development

```sh
git clone https://github.com/AndyHarman-dev/netspeed.git && cd netspeed
uv sync
uv run pytest       # unit tests, no network
uv run ruff check   # lint
uv run netspeed     # run from source
```
