"""Turn results.csv into the experiment's percentages (stdlib only).

Usage:  uv run python tests/experiment-lan-vs-wifi/compute.py [results.csv]
Prints a markdown table to paste into this folder's README.
"""

from __future__ import annotations

import csv
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

CONDITIONS = ("wifi", "lan")
METRICS = ("tool_seq_mbps", "tool_par_mbps", "speedtest_mbps")
REFERENCE = "speedtest_mbps"

# condition -> metric -> median Mbit/s
Medians = dict[str, dict[str, float]]


@dataclass(frozen=True)
class Percentages:
    gain: dict[str, float]  # metric -> LAN gain over Wi-Fi, in %
    accuracy: dict[str, dict[str, float]]  # condition -> tool metric -> tool / speedtest.net, in %


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row["condition"] not in CONDITIONS:
            raise ValueError(f"run {row['run']}: condition must be one of {CONDITIONS}")
    return rows


def medians(rows: list[dict[str, str]]) -> Medians:
    out: Medians = {}
    for cond in CONDITIONS:
        subset = [r for r in rows if r["condition"] == cond]
        if not subset:
            raise ValueError(f"no runs for condition {cond!r}")
        out[cond] = {m: statistics.median(float(r[m]) for r in subset) for m in METRICS}
    return out


def percentages(med: Medians) -> Percentages:
    def compute_gain(m: str) -> float:
        return (med["lan"][m] - med["wifi"][m]) / med["wifi"][m] * 100

    def compute_accuracy(c: str, m: str) -> float:
        return med[c][m] / med[c][REFERENCE] * 100

    gain = {m: compute_gain(m) for m in METRICS}
    accuracy = {
        c: {m: compute_accuracy(c, m) for m in METRICS if m != REFERENCE} for c in CONDITIONS
    }
    return Percentages(gain, accuracy)


def render(med: Medians, pct: Percentages) -> str:
    label = {
        "tool_seq_mbps": "netspeed (sequential)",
        "tool_par_mbps": "netspeed --parallel 4",
        "speedtest_mbps": "speedtest.net",
    }
    lines = [
        "| Measure | Wi-Fi median (Mbit/s) | LAN median (Mbit/s) | LAN gain over Wi-Fi |",
        "|---|---:|---:|---:|",
    ]
    for m in METRICS:
        lines.append(
            f"| {label[m]} | {med['wifi'][m]:.1f} | {med['lan'][m]:.1f} | {pct.gain[m]:+.1f}% |"
        )
    lines += [
        "",
        "| netspeed accuracy vs speedtest.net | Wi-Fi | LAN |",
        "|---|---:|---:|",
    ]
    for m in METRICS:
        if m == REFERENCE:
            continue
        lines.append(
            f"| {label[m]} | {pct.accuracy['wifi'][m]:.0f}% | {pct.accuracy['lan'][m]:.0f}% |"
        )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name("results.csv")
    med = medians(load(path))
    print(render(med, percentages(med)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
