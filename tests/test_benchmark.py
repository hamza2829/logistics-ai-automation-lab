import json

import pytest
import yaml

from logistics_lab.benchmark import (
    LabeledRequest,
    evaluate,
    generate_benchmark,
    read_benchmark,
    write_evaluation,
)
from logistics_lab.domain import CATEGORIES
from logistics_lab.triage import MockLLM, Triage

from .conftest import SCENARIOS

ENGINE = Triage(MockLLM())


def test_seeded_benchmark_is_balanced_labeled_and_reproducible(tmp_path):
    one, two, another = (tmp_path / name / "cases.csv" for name in ("one", "two", "three"))
    generate_benchmark(SCENARIOS, one, 2829)
    generate_benchmark(SCENARIOS, two, 2829)
    generate_benchmark(SCENARIOS, another, 2830)
    assert one.read_bytes() == two.read_bytes() != another.read_bytes()
    cases = read_benchmark(one)
    assert len(cases) == 80
    assert {case.expected for case in cases} == set(CATEGORIES)
    assert all(sum(case.expected == label for case in cases) == 16 for label in CATEGORIES)
    result = evaluate(cases, ENGINE)
    assert 0 < result.correct < result.total
    assert 0 < result.unflagged_errors <= len(result.failures)
    assert sum(sum(row.values()) for row in result.confusion.values()) == 80


def test_exact_match_accuracy_includes_review_cases_and_every_failure(tmp_path):
    cases = [
        LabeledRequest(request_id="T1", text="Route sheet.", expected="dispatch"),
        LabeledRequest(request_id="T2", text="Stock transfer | <b>demo</b>.", expected="dispatch"),
        LabeledRequest(request_id="T3", text="Someone to take the wheel.", expected="driver_booking"),
        LabeledRequest(request_id="T4", text="Please help.", expected="other"),
    ]
    result = evaluate(cases, ENGINE)
    assert (result.total, result.correct, result.accuracy_pct, result.flagged) == (4, 2, 50, 2)
    assert result.unflagged_errors == 1
    assert result.confusion["dispatch"]["dispatch"] == 1
    assert result.confusion["dispatch"]["warehouse_order"] == 1
    assert result.confusion["driver_booking"]["other"] == 1
    assert [failure.request_id for failure in result.failures] == ["T2", "T3"]
    write_evaluation(tmp_path, result)
    report = (tmp_path / "triage-evaluation.md").read_text(encoding="utf-8")
    assert "2/4 (50.00%)" in report
    assert "| T2 | dispatch | warehouse_order | 0.86 | no |" in report
    assert "| T3 | driver_booking | other | 0.20 | yes |" in report
    assert "&#124; &lt;b&gt;demo&lt;/b&gt;" in report
    assert len(json.loads((tmp_path / "triage-evaluation.json").read_text())["failures"]) == 2


@pytest.mark.parametrize(("body", "message"), [
    ("bad,headers\n", "expected columns"),
    ("request_id,text,expected\n", "nonempty"),
    ("request_id,text,expected\nSYN-1,Test,unrecognized\n", "line 2"),
    ("request_id,text,expected\nSYN-1,Test\n", "wrong number"),
    ("request_id,text,expected\nSYN-1,Test,other,extra\n", "wrong number"),
    ("request_id,text,expected\nSYN-1,Test,other\nSYN-1,Test,other\n", "unique"),
    ('request_id,text,expected\nSYN-1,"broken\n', "unexpected end"),
])
def test_bad_labeled_data(tmp_path, body, message):
    path = tmp_path / "cases.csv"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        read_benchmark(path)


@pytest.mark.parametrize(("body", "message"), [
    ("[", "scenarios.yml"),
    ("other: [text]", "expected scenarios"),
    (yaml.safe_dump({label: ["Test"] if label != "other" else [None] for label in CATEGORIES}),
     "list of nonempty texts"),
])
def test_bad_scenario_source(tmp_path, body, message):
    path = tmp_path / "scenarios.yml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        generate_benchmark(path, tmp_path / "cases.csv", 0)


def test_evaluate_requires_cases():
    with pytest.raises(ValueError, match="at least one"):
        evaluate([], ENGINE)
