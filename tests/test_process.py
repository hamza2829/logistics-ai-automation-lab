import json

import pytest

from logistics_lab.events import event_rows, generate_events
from logistics_lab.process import analyze, read_event_log, write_analysis

from .conftest import write_rows


def test_seeded_generation_is_reproducible_and_exercises_all_request_types(tmp_path):
    first, second, different = (tmp_path / f"{name}.csv" for name in ("first", "second", "other"))
    generate_events(first, 300, 2829)
    generate_events(second, 300, 2829)
    generate_events(different, 300, 2830)
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() != different.read_bytes()
    events = read_event_log(first)
    assert events.request_id.nunique() == 300
    assert set(events.request_type) == {"mail_parcel", "dispatch", "driver_booking", "warehouse_order"}
    assert set(events.priority) == {"low", "normal", "high", "urgent"}
    result = analyze(events).summary
    assert result.completed == 300
    assert 0 < result.reworked <= result.rework_events


def test_default_generator_produces_three_thousand_requests(tmp_path):
    path = tmp_path / "nested" / "log.csv"
    generate_events(path)
    result = analyze(read_event_log(path))
    assert result.summary.requests == result.summary.completed == 3000


def test_nonpositive_counts_are_rejected(tmp_path):
    path = tmp_path / "events.csv"
    with pytest.raises(ValueError, match="positive"):
        generate_events(path, count=0)
    with pytest.raises(ValueError, match="positive"):
        list(event_rows(-1, 123))
    assert not path.exists()


def test_hand_calculated_analysis_and_no_cross_request_edges(tmp_path, small_rows):
    path = write_rows(tmp_path / "events.csv", reversed(small_rows))
    result = analyze(read_event_log(path))
    assert result.summary.requests == 3
    assert result.summary.events == 19
    assert result.summary.completed == 2
    assert result.summary.reworked == result.summary.rework_events == 1
    assert result.summary.rework_rate_pct == pytest.approx(100 / 3)
    assert result.summary.median_completed_minutes == 85
    assert result.steps.iloc[0]["activity"] == "queue"
    queue = result.steps.set_index("activity").loc["queue"]
    assert queue["samples"] == 3
    assert queue["median_minutes"] == 20
    assert queue["p90_minutes"] == 28
    assert queue["total_minutes"] == 60
    assert "completed" not in result.steps["activity"].values
    graph = result.edges.set_index(["activity", "next_activity"])["count"].to_dict()
    assert graph == {
        ("received", "triage"): 3, ("triage", "queue"): 3, ("queue", "process"): 3,
        ("process", "quality_check"): 3, ("quality_check", "completed"): 2,
        ("quality_check", "rework"): 1, ("rework", "queue"): 1,
    }
    assert result.by_type.set_index("request_type").loc["mail_parcel", "reworked"] == 1


def test_rework_rate_counts_cases_once_even_with_multiple_visits(tmp_path, small_rows):
    single = small_rows[:10]
    inserted = single[5:9]
    for offset, row in enumerate(inserted, 11):
        row = row.copy()
        row[1] = offset - 1
        row[2] = f"2025-02-03T11:{(offset - 11) * 10:02d}:00+00:00"
        single.insert(-1, row)
    single[-1][1] = 14
    single[-1][2] = "2025-02-03T12:00:00+00:00"
    frame = read_event_log(write_rows(tmp_path / "events.csv", single))
    result = analyze(frame).summary
    assert (result.reworked, result.rework_events, result.rework_rate_pct) == (1, 2, 100)


@pytest.mark.parametrize(("row", "column", "value", "message"), [
    (0, 0, "bad id", "invalid request ID"),
    (0, 1, "0", "positive integers"),
    (0, 1, 2, "start at one"),
    (1, 1, 4, "increase by one"),
    (0, 2, "yesterday", "timezone"),
    (0, 2, "2025-02-03T09:00:00", "timezone"),
    (1, 2, "2025-02-03T09:00:00+00:00", "timestamps must increase"),
    (1, 2, "2025-02-03T08:59:00+00:00", "timestamps must increase"),
    (0, 3, "other", "type or priority"),
    (0, 4, "emergency", "type or priority"),
    (0, 4, "low", "stay constant"),
    (0, 5, "boot", "activity or status"),
    (0, 6, "closed", "activity or status"),
])
def test_invalid_event_values(tmp_path, small_rows, row, column, value, message):
    small_rows[row][column] = value
    with pytest.raises(ValueError, match=message):
        read_event_log(write_rows(tmp_path / "events.csv", small_rows))


@pytest.mark.parametrize(("index", "activity", "status", "message"), [
    (0, "queue", "waiting", "must start at received"),
    (1, "process", "in_progress", "invalid transition"),
])
def test_invalid_activity_order(tmp_path, small_rows, index, activity, status, message):
    small_rows[index][5:] = [activity, status]
    with pytest.raises(ValueError, match=message):
        read_event_log(write_rows(tmp_path / "events.csv", small_rows))


def test_bad_headers_empty_and_unreadable_event_log(tmp_path):
    path = tmp_path / "events.csv"
    with pytest.raises(ValueError, match="events.csv"):
        read_event_log(path)
    with pytest.raises(ValueError, match="expected columns"):
        read_event_log(write_rows(path, [], fields=("request_id",)))
    with pytest.raises(ValueError, match="event log is empty"):
        read_event_log(write_rows(path, []))


def test_report_writes_chart_markdown_and_auditable_tables(tmp_path, small_rows):
    path = write_rows(tmp_path / "events.csv", small_rows)
    out = tmp_path / "report"
    write_analysis(out, analyze(read_event_log(path)))
    assert (out / "step-times.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    report = (out / "process-report.md").read_text(encoding="utf-8")
    assert "```mermaid" in report and "quality_check -->|1| rework" in report
    assert "33.33%" in report and "85.0 min" in report
    assert (out / "requests-by-type.csv").is_file()
    assert json.loads((out / "summary.json").read_text())["requests"] == 3


def test_partial_trace_without_transitions(tmp_path, small_rows):
    result = analyze(read_event_log(write_rows(tmp_path / "events.csv", small_rows[:1])))
    assert result.summary.completed == 0
    assert result.summary.median_completed_minutes is None
    assert result.edges.empty and result.steps.empty
    write_analysis(tmp_path, result)
    report = (tmp_path / "process-report.md").read_text(encoding="utf-8")
    assert "No observed transitions." in report
    assert "Unavailable" in report
