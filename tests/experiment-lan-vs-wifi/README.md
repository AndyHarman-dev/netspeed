# Experiment: Wi-Fi vs wired LAN on a Windows laptop

## Goal

Show that a direct Ethernet connection gives a considerably faster download than Wi-Fi on the same
laptop and router, and that `netspeed` detects that difference. Cross-check both against
[speedtest.net](https://www.speedtest.net/).

The experiment reports two numbers:

1. **LAN gain over Wi-Fi**, as `(LAN - Wi-Fi) / Wi-Fi * 100%`, for each tool.
2. **netspeed accuracy**, as `netspeed / speedtest.net * 100%`, for each connection type.

## Setup

> Captured 2026-11-17.

| Item | Value |
|---|---|
| Laptop / Windows version | MECHREVO Jiaolong15K (GM5BG0E), Windows 11 Home, build 26200 |
| Router (model, Wi-Fi standard) | ISP-supplied Telecentro router (model not identified), Wi-Fi 6 (802.11ax) |
| ISP plan (advertised download) | 40 Mbit/s |
| Wi-Fi band and signal (`netsh wlan show interfaces`: Radio type, Channel, Signal, Receive rate) | 802.11ax, 5 GHz, channel 157, signal 94% (-41 dBm), receive rate 1201 Mbps |
| Ethernet link speed (`Get-NetAdapter \| ft Name,Status,LinkSpeed`) | 1 Gbps (adapter `Ethernet`, Up) |
| Test URL used by netspeed | `https://speed.cloudflare.com/__down?bytes=25000000` (default) |
| speedtest.net server (name, city) | IXP CABASE - Servidor Nacional, Buenos Aires (Telecentro) |
| netspeed version (`netspeed --version`) | 0.1.0 |


## What each tool measures

Read this before the numbers. The two tools do not measure the same thing.

- **netspeed (sequential, the default)** downloads one file 10 times, one after another, over a
  single TCP connection, from the URL you give it. On a fast link one connection often can't fill the
  line, because of TCP window size, latency to the server, and how fast the server sends.
- **netspeed `--count 12 --parallel 4`** downloads 12 files over 4 connections at once, 3 each. This is the
  like-for-like comparison with speedtest.net. The count is 12 rather than the default 10 so that 4 divides it
  evenly. With 10, the split is 3, 3, 2, 2, and the last stretch of the run would use only 2 connections.
- **speedtest.net** opens several connections at once to a nearby server picked for speed, and
  reports roughly its peak throughput.

Expected effects:

- Sequential netspeed reads **lower** than speedtest.net, more so on the faster (LAN) connection.
- That single-connection ceiling can **shrink the LAN gain** that sequential mode shows.
- `--parallel 4` should land much closer to speedtest.net and show a similar LAN gain.
- If the ISP plan is slower than the Wi-Fi link, both connections hit the plan's limit. LAN then can't
  look much better, whatever the tool, and the write-up says so.

## Protocol

1. **Prepare.** Close heavy apps and pause OneDrive, Windows Update and any downloads. Turn the VPN off. Plug the
   laptop into power. Install netspeed (see the [root README](../../README.md#install)).
2. **Define the conditions.**
   - **Wi-Fi (`wifi`):** Ethernet cable unplugged, Wi-Fi connected to the router.
   - **LAN (`lan`):** cable plugged in **and Wi-Fi turned off**. If Wi-Fi stays on, Windows may
     keep routing traffic over it.
3. **Pre-check (LAN, once).** Run `netspeed --count 12 --parallel 4` and a speedtest.net test. If netspeed reads far
   below speedtest.net (under about half), the Cloudflare default URL is a poor server for you. In that case,
   pick a large file (100 MB or more) on a nearby fast server, such as your ISP's test file or a local
   mirror, and use **that same URL in every run**. Write the URL in Setup. In speedtest.net, pick a server
   and keep it for every run.
4. **Six runs, alternating:** `wifi, lan, wifi, lan, wifi, lan`. Switch the connection between runs and
   wait about 10 seconds for it to settle. Alternating keeps a slow moment (a neighbour streaming, ISP
   congestion) from hitting only one condition. Each run takes three measurements, back to back, from
   this folder:
   ```powershell
   netspeed $URL --json > raw\wifi-1-seq.json
   netspeed $URL --count 12 --parallel 4 --json > raw\wifi-1-par.json
   # then speedtest.net in the browser (same server), note the Download Mbit/s
   ```
   (Use `lan-2-seq.json` and so on for the other runs. Leave `$URL` out if you kept the default.)
5. **Record** each run as one row in `results.csv`. Take `mbps` from the two JSON files and the download
   figure from speedtest.net:
   ```
   run,condition,tool_seq_mbps,tool_par_mbps,speedtest_mbps,timestamp,notes
   1,wifi,48.2,91.0,95.4,2026-11-18T19:02,signal 78%
   ```
6. **Compute** the medians and percentages:
   ```sh
   uv run python tests/experiment-lan-vs-wifi/compute.py
   ```
   It prints the tables for the Results section below.

## Raw results

- `results.csv`: one row per run.
- `raw/`: the full `--json` output of every netspeed run, including every request's bytes and time.

## Results

Medians of 3 runs per condition, from `compute.py`:

| Measure | Wi-Fi median (Mbit/s) | LAN median (Mbit/s) | LAN gain over Wi-Fi |
|---|---:|---:|---:|
| netspeed (sequential) | 32.4 | 32.3 | -0.3% |
| netspeed --count 12 --parallel 4 | 32.7 | 32.7 | -0.1% |
| speedtest.net | 33.8 | 33.8 | +0.0% |

| netspeed accuracy vs speedtest.net | Wi-Fi | LAN |
|---|---:|---:|
| netspeed (sequential) | 96% | 96% |
| netspeed --count 12 --parallel 4 | 97% | 97% |

Spread across the 3 runs (min to max, Mbit/s):

| Measure | Wi-Fi | LAN |
|---|---|---|
| netspeed (sequential) | 32.33 to 32.44 | 31.04 to 32.48 |
| netspeed --count 12 --parallel 4 | 32.66 to 32.80 | 32.66 to 32.74 |
| speedtest.net | 33.71 to 33.89 | 33.71 to 33.83 |

Notes on the data:

- Every request downloaded the full 25,000,000 bytes. Sequential requests took 6.03 to 6.30 s each.
- **LAN run 2, sequential (31.04 Mbit/s)** is the one outlier. Its requests took as long as in every other run
  (61.3 s in total), but its wall clock has 3.1 s outside any request, against about 0.4 s in the other runs. The
  stall was before the first request or after the last one, not in the transfer. It does not move the median
  (32.34 with or without it).
- Upload (speedtest.net only, from the `notes` column): Wi-Fi median 93.5 Mbit/s, LAN median 90.2 Mbit/s. The
  pre-check's 23% LAN deficit (one reading, 91 vs 118) shrank to about 4% over three runs each, which is
  within run-to-run noise (86 to 99 Mbit/s across all six runs).

## Conclusion

**On this connection, wired LAN is not faster than Wi-Fi.** All three measures put the gain at 0% (-0.3% to
+0.0%), well inside the run-to-run spread. The hypothesis in the Goal is not confirmed here, and the reason is
the setup rather than the tools: the ISP plan is 40 Mbit/s, and both Wi-Fi (1201 Mbit/s link, -41 dBm) and
Ethernet (1 Gbps) are more than 25 times faster than that. Both connections hit the plan's limit, about 33 to 34
Mbit/s (roughly 84% of the advertised 40), which is the case the expected effects warned about.

**netspeed shows the same picture as speedtest.net.** It finds no difference where speedtest.net finds none, and
it reads 96 to 97% of speedtest.net's figure on both connections. The 3 to 4% gap is consistent with
speedtest.net reporting closer to peak throughput, while netspeed averages over the whole run, including
connection setup and the start of each transfer.

Which expected effects showed up:

- *Sequential reads lower than speedtest.net:* only slightly (96%), and not more so on LAN. At 33 Mbit/s one
  connection can fill the line, so the single-connection ceiling never came into play.
- *Sequential shrinks the LAN gain:* not testable, since there was no gain to shrink.
- *`--parallel 4` lands closer to speedtest.net:* yes, but only by about one point (97% vs 96%), for the same reason.
- *Plan slower than the Wi-Fi link:* yes. This is the effect that decided the result.

To actually show a LAN advantage, repeat the experiment where the line is faster than the Wi-Fi: a plan of
several hundred Mbit/s or more, or a weaker Wi-Fi signal (another room, the 2.4 GHz band), or a LAN-local
download server, which takes the ISP out of the path.

## How it was tested (brief)

On 2026-11-17, between 22:50 and 23:30 UTC, in Buenos Aires, on the laptop and router in Setup, with
netspeed 0.1.0 and the default Cloudflare URL. A pre-check ([`precheck-findings.md`](precheck-findings.md))
confirmed that the default URL reads within 3% of speedtest.net, so no URL change was needed. Six runs then
alternated Wi-Fi and LAN (Wi-Fi off for LAN). Each run took a sequential netspeed measurement (10 x 25 MB), a
`--count 12 --parallel 4` measurement, and a speedtest.net test against the same server (IXP CABASE, Buenos
Aires). The tables use the median of the 3 runs per condition. The pre-check log notes that Tailscale was up;
whether it was switched off for the six runs was not recorded. The run 2 LAN sequential stall above is the only
irregularity.
