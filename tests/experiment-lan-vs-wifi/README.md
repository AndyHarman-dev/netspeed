# Experiment: Wi-Fi vs wired LAN on a Windows laptop

## Goal

Show that a direct Ethernet connection gives a considerably faster download than Wi-Fi on the same
laptop and router, and that `netspeed` detects that difference. Cross-check both against
[speedtest.net](https://www.speedtest.net/).

The experiment reports two numbers:

1. **LAN gain over Wi-Fi**, as `(LAN - Wi-Fi) / Wi-Fi * 100%`, for each tool.
2. **netspeed accuracy**, as `netspeed / speedtest.net * 100%`, for each connection type.

## Setup

> Fill this in before the first run.

| Item | Value |
|---|---|
| Laptop / Windows version | |
| Router (model, Wi-Fi standard) | |
| ISP plan (advertised download) | |
| Wi-Fi band and signal (`netsh wlan show interfaces`: Radio type, Channel, Signal, Receive rate) | |
| Ethernet link speed (`Get-NetAdapter \| ft Name,Status,LinkSpeed`) | |
| Test URL used by netspeed | |
| speedtest.net server (name, city) | |
| netspeed version (`netspeed --version`) | |

## What each tool measures

Read this before the numbers. The two tools do not measure the same thing.

- **netspeed (sequential, the default)** downloads one file 10 times, one after another, over a
  single TCP connection, from the URL you give it. On a fast link one connection often can't fill the
  line, because of TCP window size, latency to the server, and how fast the server sends.
- **netspeed `--parallel 4`** downloads the same 10 files over 4 connections at once. This is the
  like-for-like comparison with speedtest.net.
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
3. **Pre-check (LAN, once).** Run `netspeed --parallel 4` and a speedtest.net test. If netspeed reads far
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
   netspeed $URL --parallel 4 --json > raw\wifi-1-par.json
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

> Paste the `compute.py` output here.

## Conclusion

> To be written from the results. Cover:
> - The LAN-over-Wi-Fi gain by each tool.
> - Whether netspeed shows the difference.
> - How close it is to speedtest.net.
> - Which of the expected effects above showed up.

## How it was tested (brief)

> One paragraph: date, place, the conditions, 3 alternating runs each, medians, and anything unusual.
