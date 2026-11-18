# Pre-check findings (2026-11-17)

Pre-checks run before the six experiment runs. These are not experiment runs and are not in `results.csv`.

## Conditions

- URL: `https://speed.cloudflare.com/__down?bytes=25000000` (default)
- netspeed command: `netspeed --count 12 --parallel 4`
- speedtest.net server: IXP CABASE - Servidor Nacional, Buenos Aires (Telecentro)
- ISP plan: **40 Mbit/s download** (advertised)
- Ethernet link speed: **1 Gbps** (`Get-NetAdapter`, adapter `Ethernet`, Up)
- Wi-Fi: 802.11ax, 5 GHz, receive rate 1201 Mbps (see README Setup)

## Results

| Connection | netspeed (par 4), Mbit/s | speedtest.net download, Mbit/s | speedtest.net upload, Mbit/s |
|---|---|---|---|
| LAN | 32.80 | 33.63 | 91.24 (1 run) |
| Wi-Fi | 32.78 | 33.65 / 32.71 / 33.56 (median 33.56) | 117.65 / 120.97 / 118.38 (median 118.38) |

## Findings

1. **The Cloudflare default URL is fine.** netspeed reads about 97.5% of speedtest.net on LAN
   (32.80 vs 33.63) and about 98% on Wi-Fi (32.78 vs 33.56 median). This is far above the
   "under half" threshold in the protocol, so no URL change is needed.
2. **Download is capped by the plan.** About 33 Mbit/s is roughly 82% of the 40 Mbit/s plan. Wi-Fi and
   LAN are identical within noise, so the main experiment will likely show no LAN gain on download.
   The README already anticipates this outcome; the write-up should say so.
3. **Upload looks different, in the opposite direction to the hypothesis.** Wi-Fi upload (about 118
   Mbit/s) was higher than the single LAN reading (91 Mbit/s), about 23% lower on LAN. Only one LAN
   reading exists, and the LAN ping was jittery (15/35/157 ms), so this may be noise.
4. **The wired link is not the cause.** The adapter negotiated 1 Gbps, which rules out a 100 Mbit/s
   (Fast Ethernet) limit.

## Open items

- Take 3 more LAN speedtest.net runs (same server) and record upload each time. If LAN upload stays near
  90 Mbit/s, the difference is real. If it rises to around 118, the first reading was noise.
- Tailscale was Up during the checks. Check for an enabled exit node (`tailscale status`) and turn it
  off for the runs, per the protocol's "VPN off".
- netspeed measures download only. Upload data can only come from speedtest.net. If upload becomes the
  focus, netspeed would need an upload mode (branch, tests and README update per `CLAUDE.md`).
- Setup table TODOs now answerable: ISP plan = 40 Mbit/s, Ethernet link = 1 Gbps, speedtest.net server =
  IXP CABASE - Servidor Nacional, Buenos Aires. They have not been edited into the README yet.
