# CLAUDE.md

`netspeed` is a cross-platform Python CLI. It fetches a URL N times (10 by default, sequentially) and prints
the average request time, the total downloaded data and the download speed in Mbit/s.

## Layout

- `src/netspeed/stats.py`: pure maths (speed, average, units). It does no I/O.
- `src/netspeed/measure.py`: the httpx request loop. Timing goes through an injectable `clock`, and HTTP goes through an
  injectable `transport` (`httpx.MockTransport` in tests).
- `src/netspeed/cli.py`: argparse, output formatting and exit codes. Progress goes to stderr; the summary or JSON goes to stdout.
- `tests/unit/`: pytest. This is the only collected test path.
- `tests/experiment-lan-vs-wifi/`: the manual Wi-Fi vs LAN experiment (protocol, CSV, `compute.py`).
- `.claude/plans/`: implementation plans.

## Commands

```sh
uv sync                 # install the project + dev deps into .venv
uv run netspeed --help  # run the CLI from source
uv run pytest           # unit tests (no network)
uv run ruff check       # lint
uv run ruff format      # format
```

## Conventions

- **Name:** the tool is `netspeed`. Never call it "speedtest", and don't associate it with Ookla.
  speedtest.net is mentioned only as the experiment's reference.
- **Units:** speed is Mbit/s (10^6 bit/s) and data is MB (10^6 bytes).
  Speed = `total_bytes * 8 / wall_clock_seconds / 1e6`.
- **Default mode:** `--parallel 1` is the specified sequential behaviour. Do not change its semantics;
  `--parallel N` exists only for the speedtest.net comparison.
- **Console output:** ASCII only (Windows consoles).
- **Exit codes:** 0 ok, 1 network/HTTP error, 2 bad arguments.
- **Unit tests:** never hit the network. Use `httpx.MockTransport` and a fake clock.
- **Docs:** update README.md and this file with every user-visible change.
- **Experiment:** it stays in `tests/experiment-lan-vs-wifi/`. The root README only links to it.
- **Git:** work on branches and never commit to `main` directly.
