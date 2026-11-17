import importlib.util
import sys
from pathlib import Path

import pytest

PATH = Path(__file__).parents[1] / "experiment-lan-vs-wifi" / "compute.py"
spec = importlib.util.spec_from_file_location("compute", PATH)
compute = importlib.util.module_from_spec(spec)
sys.modules["compute"] = compute  # dataclasses resolve their module here
spec.loader.exec_module(compute)

CSV = """run,condition,tool_seq_mbps,tool_par_mbps,speedtest_mbps,timestamp,notes
1,wifi,40,80,100,t,
2,lan,90,180,200,t,
3,wifi,50,90,110,t,
4,lan,95,190,210,t,
5,wifi,45,85,90,t,
6,lan,85,170,190,t,
"""


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "results.csv"
    p.write_text(CSV)
    return p


def test_medians_per_condition(csv_path):
    med = compute.medians(compute.load(csv_path))
    assert med["wifi"] == {"tool_seq_mbps": 45, "tool_par_mbps": 85, "speedtest_mbps": 100}
    assert med["lan"] == {"tool_seq_mbps": 90, "tool_par_mbps": 180, "speedtest_mbps": 200}


def test_lan_gain_over_wifi_in_percent(csv_path):
    pct = compute.percentages(compute.medians(compute.load(csv_path)))
    assert pct.gain == pytest.approx(
        {"tool_seq_mbps": 100.0, "tool_par_mbps": (180 - 85) / 85 * 100, "speedtest_mbps": 100.0}
    )


def test_accuracy_is_tool_over_speedtest_per_condition(csv_path):
    pct = compute.percentages(compute.medians(compute.load(csv_path)))
    assert pct.accuracy["wifi"] == pytest.approx({"tool_seq_mbps": 45.0, "tool_par_mbps": 85.0})
    assert pct.accuracy["lan"] == pytest.approx({"tool_seq_mbps": 45.0, "tool_par_mbps": 90.0})


def test_render_prints_markdown_tables(csv_path, capsys):
    assert compute.main(["compute.py", str(csv_path)]) == 0
    out = capsys.readouterr().out
    assert "| netspeed --parallel 4 | 85.0 | 180.0 | +111.8% |" in out
    assert "| speedtest.net | 100.0 | 200.0 | +100.0% |" in out
    assert "| netspeed (sequential) | 45% | 45% |" in out


def test_unknown_condition_is_rejected(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text(
        "run,condition,tool_seq_mbps,tool_par_mbps,speedtest_mbps,timestamp,notes\n"
        "1,ethernet,1,1,1,t,\n"
    )
    with pytest.raises(ValueError, match="condition"):
        compute.load(p)


def test_missing_condition_is_rejected(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text(
        "run,condition,tool_seq_mbps,tool_par_mbps,speedtest_mbps,timestamp,notes\n"
        "1,wifi,1,1,1,t,\n"
    )
    with pytest.raises(ValueError, match="lan"):
        compute.medians(compute.load(p))
