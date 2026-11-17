---
status: Pending
---

# Plan: cross-platform internet speed CLI (Python) + LAN vs Wi-Fi experiment

## Context

Greenfield repo at `~/dev/speedtest`, remote `origin` = `https://github.com/AndyHarman-dev/speedtest.git`
(empty on GitHub as of 2026-11-17). Scaffold branch: `chore/scaffold`.

Assignment (verbatim scope):
- Accept the address to knock on (e.g. a heavy picture).
- Make 10 sequential requests, waiting for the full response to each.
- Calculate the average request time and the total amount of downloaded data.
- Print the download speed to the console. Units are our choice and must be documented in README.
- Put it on GitHub with a README holding start instructions.

Then prove it works: on the user's Windows laptop, compare Wi-Fi against wired Ethernet, cross-checked
against speedtest.net. Report (a) the % gain of LAN over Wi-Fi and (b) our tool's accuracy relative to
speedtest.net. The experiment lives in `tests/experiment-lan-vs-wifi/` and stays separate from the
root README/CLAUDE.md. The root README only links to it.

## Decisions locked (from the 2026-11-17 interview)

| Topic | Decision |
|---|---|
| Distribution | `uv tool install git+https://github.com/AndyHarman-dev/speedtest.git`. uv provisions Python on Windows, so there is no separate install. |
| Packaging | `pyproject.toml`, src layout, hatchling build backend, `requires-python >= 3.10` |
| HTTP | `httpx` (the only runtime dependency) |
| CLI parsing | stdlib `argparse`, to avoid a second dependency |
| Units | **Mbit/s** (10^6 bits/s, same as speedtest.net). Data volume shown in **MB** (10^6 bytes). |
| Speed formula | `total_bytes × 8 / wall_clock_seconds / 1e6` (aggregate). The wall clock runs from the first request's start to the last request's end. In sequential mode that equals the sum of request times plus a negligible gap. The average request time (mean of per-request durations) is printed separately. |
| Connections | One keep-alive client by default, with a random cache-busting query param per request. `--no-keepalive` opens a fresh client per request. |
| Flags | `URL` (optional positional, default test file), `--count` (default 10), `--timeout` (seconds), `--json`, `--no-keepalive`, `--parallel N` (default 1), `--version` |
| Default URL | `https://speed.cloudflare.com/__down?bytes=25000000` (25 MB, uncached, global CDN) |
| Tests layout | `tests/unit/` (pytest, the only collected path) + `tests/experiment-lan-vs-wifi/` (manual experiment) |
| Experiment baseline | Same router: Wi-Fi vs Ethernet cable |
| Experiment trials | 3 alternating runs per condition (W, L, W, L, W, L), with medians used for every % |
| Reported % | LAN gain over Wi-Fi (tool and speedtest.net), plus tool ÷ speedtest.net per condition |
| CI | GitHub Actions: ruff + pytest on ubuntu / windows / macos |
| Git | `main` pushed to GitHub as the default branch (user OK, 2026-11-17). Feature work happens on branches off `main`. |
| Command / package name | `speedtest` (user decision 2026-11-17, overriding the proposed `netspeed`) |
| `--parallel N` | Optional, default `1`, which is the specified sequential behaviour and stays untouched. `N > 1` spreads the same `--count` requests over N concurrent connections. It exists **only** to give an apples-to-apples comparison with speedtest.net's multi-stream test. |

**Name-clash note.** The command `speedtest` shares its name with Ookla's official CLI and `speedtest-cli`. uv installs
tools in isolated environments, so the Python import never clashes. Only PATH order matters if one of those is also
installed. The README gets a "check with `where speedtest` (Windows) / `which speedtest`" note, and `speedtest --version`
prints our own name and version so the user can tell which one ran.

## Target layout

```
speedtest/
├── .github/workflows/ci.yml
├── .claude/plans/
├── src/speedtest/
│   ├── __init__.py        # __version__
│   ├── __main__.py        # python -m speedtest
│   ├── cli.py             # argparse, output formatting, exit codes
│   ├── measure.py         # httpx request loop, timing (injectable transport + clock)
│   └── stats.py           # pure maths: aggregate speed, avg time, unit conversion
├── tests/
│   ├── unit/              # pytest
│   └── experiment-lan-vs-wifi/
│       ├── README.md      # protocol + results + conclusions
│       ├── results.csv    # raw numbers, one row per run
│       ├── raw/           # --json outputs of each tool run
│       └── compute.py     # stdlib-only: CSV → medians → percentages (markdown table)
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## Phase 0 — Scaffold (mostly done)

**Model: Sonnet 5** — Mechanical git and file housekeeping. No axis is in the Opus column.

**Current State.** `~/dev/speedtest` is git-initialised on `chore/scaffold` with `origin` set. It holds empty
`README.md`/`CLAUDE.md`, `.claude/plans/` and `tests/`. Nothing is committed yet, and the GitHub repo is empty.

**Desired State.** The scaffold and this plan are committed on `chore/scaffold`. Once the plan is approved,
GitHub has a sensible default branch.

**Problems.**
1. The GitHub repo is empty, so **the first branch pushed becomes GitHub's default branch**. Pushing
   `chore/scaffold` first would make it the default.
2. Your branch policy forbids committing directly to `main`, but `main` has no commits yet.

**Solutions.**
- Commit the scaffold and plan on `chore/scaffold` (`chore: scaffold repo and plan`).
- After approval, with an explicit "yes": fast-forward `main` to the scaffold commit (`git branch -f main chore/scaffold`,
  which is a merge with nothing else on main), push `main` first so it becomes the default, then push feature branches.
  *Escalate/stop if:* you'd rather GitHub's default be something other than `main`.

## Phase 1 — Project skeleton

**Model: Sonnet 5** — Standard uv/hatchling boilerplate. `uv sync` and `uv run pytest` fail loudly if it's wrong.

**Current State.** There is no Python project.

**Desired State.** `uv sync` works, `uv run speedtest --help` prints usage, `uv run pytest` collects
`tests/unit` only, and `uv run ruff check` is clean. CLAUDE.md holds the dev commands and conventions.

**Problems.** pytest would try to collect `tests/experiment-lan-vs-wifi/compute.py` and its folder.

**Solutions.**
```toml
[project]
name = "speedtest"
requires-python = ">=3.10"
dependencies = ["httpx>=0.27"]
[project.scripts]
speedtest = "speedtest.cli:main"
[dependency-groups]
dev = ["pytest", "ruff"]
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```
- Add a `.gitignore` (venv, `__pycache__`, dist, `.ruff_cache`) and pin `.python-version` to 3.12.
- CLAUDE.md gets the purpose, layout, commands (`uv sync`, `uv run pytest`, `uv run ruff check`, `uv run speedtest`),
  the rules "keep README/CLAUDE.md updated with every user-visible change" and "the experiment lives only in tests/experiment-*".

## Phase 2 — Measurement core (`stats.py`, `measure.py`)

**Model: Sonnet 5** — The formula and semantics are locked above. Timing is made deterministic through an
injected clock plus `httpx.MockTransport`, so tests fail loudly on wrong maths or wrong byte counting.
**Escalate/stop if:** httpx transparently decompresses and the byte counts differ from wire bytes in a way
`Accept-Encoding: identity` doesn't fix. That changes what "downloaded data" means and needs a decision.

**Current State.** Nothing exists.

**Desired State.** `run(url, count, timeout, keepalive, transport=None, clock=time.perf_counter) -> RunResult`
returns per-request `(status, bytes, seconds)`, and `stats.summarise(...)` produces totals, the average, and Mbit/s.

**Problems / risks.**
1. **Caching**: repeated identical GETs can be served by a local or CDN cache, which inflates speed.
2. **Compression**: if the server gzips, decoded bytes ≠ bytes on the wire.
3. **"Full answer"**: we must read the whole body. Headers arriving is not enough.
4. **Timing boundaries**: the timer must include request send through the last body byte, or "request time" lies.
5. Errors partway through (non-2xx, timeouts, connection resets) must not produce a fake speed.

**Solutions.**
- Append `_nocache=<uuid4 hex>` to each request URL, merged into the existing query string with `httpx.URL.copy_merge_params`.
  Also send `Cache-Control: no-cache`.
- Send `Accept-Encoding: identity` and count raw bytes from `response.iter_raw()`, which is wire-level body bytes.
- Per request: `t0 = clock()` → `client.stream("GET", ...)` → consume `iter_raw()` fully → `t1 = clock()`.
- Call `raise_for_status()` before consuming. Any exception aborts the run with a typed error (`MeasureError`),
  and no partial speed is reported.
- With `keepalive=False`, create a fresh `httpx.Client` per request. Otherwise use one client for the whole run.
  `follow_redirects=True`.
- `stats.py`: `mbps = total_bytes * 8 / wall_seconds / 1e6`, `avg_s = sum(request_seconds) / n`, `total_mb = total_bytes / 1e6`.
  `RunResult` carries `wall_seconds` (run_end − run_start) from the start, so Phase 2b doesn't have to change the maths.
  Guard against zero seconds and zero bytes.
- Unit tests: maths (known inputs → exact output), cache-bust param appended and existing params preserved,
  byte counting over a MockTransport body, fake clock → exact timings, a 404 raises, keepalive=False
  builds N clients (spy), and count is respected.

## Phase 2b — `--parallel N` (comparison mode)

**Model: Sonnet 5** — A thread pool over the Phase 2 single-request function. Correctness is checkable with
MockTransport plus a fake clock: total bytes, request count, and wall-clock vs per-request times.
**Escalate/stop if:** sharing a single `httpx.Client` across threads shows contention or errors. In that case switch to
one client per worker. If *that* still serialises (wall clock ≈ sum of request times in a live run), stop. The
concurrency model then needs a rethink, possibly `httpx.AsyncClient`, before going further.

**Current State.** After Phase 2, only sequential runs exist.

**Desired State.** `run(..., parallel=N)` runs the same `count` requests across N workers. Each worker owns one
`httpx.Client` (keep-alive per worker, or fresh per request with `--no-keepalive`). With `parallel=1` the code path is
**identical** to the sequential mode, so the specified feature set is unchanged.

**Problems.**
1. A summed duration is meaningless under concurrency, because overlapping requests would be double-counted.
2. One failing worker must not leave the others running or report a partial speed.
3. `--parallel` larger than `--count` would leave idle workers.

**Solutions.**
- Use `concurrent.futures.ThreadPoolExecutor(max_workers=N)`. Request indices come from a shared queue, and each worker
  uses its own client (created lazily in a `threading.local`).
- Record `run_start = clock()` before submitting and `run_end = clock()` after all futures finish. Speed uses that wall
  clock (the formula in the decisions table). Per-request durations are still recorded for the average.
- On the first exception: cancel pending futures, close clients, and raise `MeasureError`.
- Clamp `N` to `count`, and warn on stderr when clamped.
- Unit tests:
  - `parallel=1` produces the same result as the sequential path.
  - `parallel=4, count=10` gives 10 requests and correct total bytes.
  - With a fake clock where requests overlap, wall clock < sum and Mbit/s uses the wall clock.
  - A failing request raises and reports no speed.
  - The clamp warning fires.

## Phase 3 — CLI (`cli.py`)

**Model: Sonnet 5** — Thin argparse layer over Phase 2. Behaviour is fully specified and testable by calling `main(argv)` and
capturing stdout/exit codes.

**Current State.** There is no entry point.

**Desired State.**
```
$ speedtest https://example.com/big.jpg
Knocking on https://example.com/big.jpg — 10 requests, keep-alive
  #1  2.31 s  25.00 MB
  ...
Requests:          10
Average request:   2.284 s
Downloaded total:  250.00 MB
Download speed:    87.56 Mbit/s
```
`--json` prints a single JSON object (url, count, parallel, keepalive, per-request list, totals, wall-clock
seconds, `mbps`, `timestamp`, `version`) and nothing else on stdout. With `--parallel N` the header reads
`10 requests over 4 parallel connections, keep-alive`. `--version` prints `speedtest (AndyHarman-dev) X.Y.Z`, so it is
distinguishable from Ookla's CLI.

**Problems.**
1. Windows consoles may choke on non-ASCII (`—`, `·`).
2. Progress lines would pollute `--json` output.

**Solutions.**
- Output is ASCII only (`-` not `—`). Progress lines go to stderr, and the summary or JSON goes to stdout.
- Exit codes: `0` ok, `1` network/HTTP error (message on stderr), `2` bad args (argparse default).
- Validation: `--count >= 1`, `--parallel >= 1`, `--timeout > 0`, URL must be http(s).
- Tests: `main([...])` with a monkeypatched `measure.run` → text format, JSON is valid and parseable, error exit 1,
  bad count exit 2.

## Phase 4 — README, CLAUDE.md, CI

**Model: Sonnet 5** — Documentation and a standard Actions matrix. CI itself verifies the workflow on all three OSes.

**Current State.** README/CLAUDE.md are empty, and there is no CI.

**Desired State.** README covers what the tool does, install (uv on Windows/macOS/Linux, including the uv install one-liners),
usage and flags, **units section** (Mbit/s = 10^6 bit/s, MB = 10^6 bytes, formula), how measurement works (sequential,
full body, cache-bust, keep-alive), the optional `--parallel N` comparison mode (and why it exists), limits (a single
TCP stream reads lower than multi-stream speedtest.net on fast links), a PATH note about Ookla's `speedtest`
(`where speedtest` / `speedtest --version`), and a link to `tests/experiment-lan-vs-wifi/README.md`. CI is green on ubuntu, windows and macos.

**Solutions.**
- `.github/workflows/ci.yml`: `astral-sh/setup-uv`, matrix `os × python [3.10, 3.13]`,
  `uv sync`, `uv run ruff check`, `uv run pytest`, plus a smoke test `uv run speedtest --help`.
  No live network test in CI, because it would be flaky.

## Phase 5 — Experiment kit (`tests/experiment-lan-vs-wifi/`)

**Model: Sonnet 5** — A protocol doc plus a small stdlib calculator with unit tests. The only judgment is protocol
design, and that is written out below.

**Current State.** The folder doesn't exist.

**Desired State.** You can follow a step-by-step protocol on Windows, paste numbers into `results.csv`,
run `uv run python tests/experiment-lan-vs-wifi/compute.py` and get a markdown table with the percentages.

**Problems / threats to validity.**
1. **Windows may keep routing over Wi-Fi while the cable is plugged in**, so the "LAN" run silently measures Wi-Fi.
2. **Single-stream vs multi-stream**: our tool will likely read below speedtest.net. That's expected, and the
   accuracy % should show it honestly, not hide it. The less obvious effect is that it can also **compress the
   LAN gain**. If one TCP stream to the test server tops out below the wired line rate, the tool's LAN number hits
   that ceiling, and the tool shows a smaller LAN-over-Wi-Fi gain than speedtest.net does.
3. **The ISP plan as the ceiling**: if the plan is slower than the Wi-Fi link, LAN won't look "considerably better".
   The report must say what was measured, not what was hoped for.
4. Time-of-day and congestion drift, which alternating runs mitigate.
5. Different servers: speedtest.net picks a nearby server, while our default hits the Cloudflare edge.

**Solutions.**
- Protocol in the experiment README:
  1. Record setup: laptop model, Windows version, router, ISP plan speed, Wi-Fi band/signal
     (`netsh wlan show interfaces`), Ethernet link speed (`Get-NetAdapter | ft Name,Status,LinkSpeed`).
  2. Wi-Fi condition: cable unplugged. LAN condition: cable plugged **and Wi-Fi turned off** (fixes problem 1).
  3. Close heavy apps and pause OneDrive and Windows Update. VPN off.
  4. Before the real runs, do one LAN pre-check against the default Cloudflare URL (anycast, so it is served from a
     nearby edge). If it reads far below speedtest.net on LAN, pick a large file on a nearby fast server
     (e.g. your ISP's or a local mirror's test file), use that same URL for **every** run, and record it.
  5. Order W, L, W, L, W, L. Each run has three back-to-back measurements:
     - `speedtest --json > raw/<cond>-<n>-seq.json` (the specified mode)
     - `speedtest --parallel 4 --json > raw/<cond>-<n>-par.json` (comparison mode)
     - speedtest.net in the browser, using the same server for every run (note the server name). Record the download Mbit/s.
  6. Fill `results.csv`: `run,condition,tool_seq_mbps,tool_par_mbps,speedtest_mbps,timestamp,notes`.
- `compute.py` (stdlib only): medians per condition →
  - LAN gain, separately for `tool_seq`, `tool_par` and `speedtest.net`: `(L − W) / W × 100%`
  - Accuracy per condition for both modes: `tool_par / speedtest × 100%` (the apples-to-apples headline) and
    `tool_seq / speedtest × 100%` (shows the single-stream ceiling)
  - Prints a markdown table to paste into the README. Unit tests for it live in `tests/unit/test_experiment_compute.py`
    (import by path).
- README sections: Goal, Setup, **"What each tool measures"** (single sequential stream to one URL vs speedtest.net's
  multi-stream test to a nearby server, explained *before* any numbers), Protocol, Raw results, Results (table),
  Conclusion. The conclusion emphasises the LAN-vs-Wi-Fi % difference and states the caveats above.

## Phase 6 — Run the experiment (user action) and write it up

**Model: Sonnet 5** — Filling in numbers and writing prose from the data you provide.
**Escalate/stop if:**
- Either tool mode's LAN gain **disagrees in sign** with speedtest.net's, or either accuracy figure is **above ~120%**
  (most likely a cache hit or a byte-counting bug). That is a likely tool or protocol bug, so debug before writing anything.
- **`--parallel` accuracy is under ~50%**, or its LAN gain is under half of speedtest.net's. Parallel mode is the
  apples-to-apples comparison, so a gap this large points at the test URL or server (rerun with a nearer or faster URL) or
  at Phase 2b. Investigate before writing conclusions.
- A low *sequential* accuracy or compressed sequential gain, **while parallel looks fine**, is the expected
  single-stream ceiling (threat 2). Document it; it is not a failure.

**Current State.** The kit exists, with no data.

**Desired State.** `results.csv` and `raw/*.json` are filled, and the README has the results table and a brief
"how I tested" write-up with the headline % difference.

**Solutions.** You run the protocol on Windows and send back (or commit) the CSV and JSON files. The session runs
`compute.py`, writes the Results and Conclusion, and links them from the root README.

## Phase 7 — Review and MR

**Model: Sonnet 5** — Routine review pass via `/code-review low` (Sonnet), triaged by the main session.

- `cd ~/dev/speedtest`, confirm the branch, run `/code-review low <branch>`, triage findings (apply, reject or escalate).
- Ask whether to open a PR into `main`.

**Routing:** All phases → Sonnet 5. Tripwires: Phase 2 (compression/byte semantics), Phase 2b (concurrency serialising), Phase 6 (implausible results).

---

## Verification summary

| Phase | Check |
|---|---|
| 1 | `uv sync && uv run speedtest --help && uv run pytest && uv run ruff check` |
| 2–3 | Unit tests green. A live `--parallel 4` run has wall clock clearly below the sum of request times. A manual `uv run speedtest` against the default URL prints a plausible Mbit/s, which is cross-checked against speedtest.net on the Mac. |
| 4 | CI green on all 3 OSes |
| 5 | `compute.py` unit tests green. A dry run on a sample CSV prints the table. |
| 6 | Real Windows numbers in the CSV. Both tool modes' gains have the same sign as speedtest.net's, and `--parallel` accuracy is within ~50–120%. |

## Change Log

- **2026-11-17**: context: scaffold the greenfield repo and plan the CLI. Actions: created `~/dev/speedtest`,
  `git init -b main`, added `origin`, branched `chore/scaffold`, created empty README.md/CLAUDE.md, `.claude/plans/`, `tests/`.
  Interviewed the user (12 questions) and wrote this plan. Decisions: proposed the command name `netspeed` to avoid shadowing
  Ookla's `speedtest`. Flagged that the first push to the empty GitHub repo sets the default branch. Verification: unverified
  (nothing implemented yet).
- **2026-11-17**: context: a side-agent note on single-stream vs speedtest.net multi-stream. Actions: added the
  LAN-gain-compression threat, a LAN pre-check step to pick a nearby test URL, and a "What each tool measures" section
  ahead of the results. Split the Phase 6 tripwire into "likely bug" (sign mismatch, >120%) and "expected
  ceiling" (low accuracy or compressed gain → try a nearer URL, then document). Verification: unverified (plan-only change).
- **2026-11-17**: context: user decisions are command name `speedtest`, an optional `--parallel` for the speedtest.net
  comparison, and pushing `main` as the default. Actions: renamed netspeed → speedtest and added a PATH/`--version` note for the Ookla clash.
  Added Phase 2b (`--parallel N`, default 1, which leaves the specified sequential mode unchanged). Changed the speed formula to
  wall clock so it is correct under concurrency (identical in sequential mode). The experiment now records seq, par and
  speedtest.net per run, and the Phase 6 tripwires key on parallel accuracy. Fast-forwarded `main` to the scaffold+plan commits and
  pushed it as the GitHub default. Verification: push verified via `git ls-remote --symref`. The plan itself is still under user review.

## Decisions Log

