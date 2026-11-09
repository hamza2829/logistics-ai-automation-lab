import csv
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from logistics_lab.cli import main
from logistics_lab.events import FIELDS, STATUS

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "fixtures" / "triage-scenarios.yml"
SCORECARD = ROOT / "config" / "use-cases.yml"


def write_rows(path, rows, fields=FIELDS):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    return path


@pytest.fixture
def small_rows():
    start = datetime(2025, 2, 3, 9, tzinfo=UTC)
    traces = [
        ("A", "mail_parcel", [
            ("received", 0), ("triage", 5), ("queue", 10), ("process", 40),
            ("quality_check", 60), ("rework", 65), ("queue", 75), ("process", 95),
            ("quality_check", 110), ("completed", 115),
        ]),
        ("B", "dispatch", [
            ("received", 0), ("triage", 5), ("queue", 15), ("process", 25),
            ("quality_check", 45), ("completed", 55),
        ]),
        ("C", "driver_booking", [("received", 0), ("triage", 7), ("queue", 10)]),
    ]
    return [
        [request, index, (start + timedelta(minutes=minute)).isoformat(),
         category, "normal", activity, STATUS[activity]]
        for request, category, trace in traces
        for index, (activity, minute) in enumerate(trace, 1)
    ]


@pytest.fixture
def invoke(monkeypatch):
    def run(*args):
        monkeypatch.setattr(sys, "argv", ["logistics-lab", *map(str, args)])
        return main()
    return run
