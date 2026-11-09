import json

import pytest

from .conftest import SCENARIOS, SCORECARD


def test_all_cli_commands(invoke, tmp_path, capsys):
    events, process, ranked, cases, benchmark = (
        tmp_path / item for item in ("events.csv", "process", "use-cases.md", "cases.csv", "eval")
    )
    assert invoke("generate", "--output", events, "--count", 12, "--seed", 89) == 0
    assert invoke("analyze", "--events", events, "--out", process) == 0
    assert invoke("rank", "--cases", SCORECARD, "--output", ranked) == 0
    assert invoke("make-benchmark", "--scenarios", SCENARIOS, "--output", cases) == 0
    assert invoke("evaluate", "--cases", cases, "--out", benchmark) == 0
    assert (process / "step-times.png").is_file() and ranked.is_file()
    assert json.loads((benchmark / "triage-evaluation.json").read_text())["total"] == 80
    assert "Mock accuracy" in capsys.readouterr().out


def test_cli_reports_invalid_count(invoke, tmp_path, capsys):
    with pytest.raises(SystemExit, match="2"):
        invoke("generate", "--count", "0", "--output", tmp_path / "events.csv")
    assert "request count must be positive" in capsys.readouterr().err
