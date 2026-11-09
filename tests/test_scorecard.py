from dataclasses import replace

import pytest
import yaml

from logistics_lab.scorecard import load_cases, rank, scorecard, write_scorecard

from .conftest import SCORECARD


def test_ranks_hypotheses_and_holds_higher_risk_cases(tmp_path):
    cases = load_cases(SCORECARD)
    assert 6 <= len(cases) <= 8
    ordered = rank(cases)
    assert ordered[0].id == "intake-triage"
    assert ordered[0].score == 2 * 5 - 1 - 2 * 2 == 5
    assert ordered[-1].id == "driver-slot-assist"
    output = tmp_path / "docs" / "use-cases.md"
    write_scorecard(SCORECARD, output)
    result = output.read_text(encoding="utf-8")
    assert result == scorecard(cases)
    assert result.count("Hold for assessment") == 2
    assert "workshop assumptions" in result
    assert "Missing-field recall" in result


def test_ranking_breaks_ties_by_risk_effort_then_id():
    original = load_cases(SCORECARD)[0]
    choices = [
        replace(original, id="z", impact=5, effort=4, risk=2),
        replace(original, id="c", impact=4, effort=2, risk=2),
        replace(original, id="b", impact=4, effort=2, risk=2),
        replace(original, id="a", impact=3, effort=2, risk=1),
    ]
    assert {case.score for case in choices} == {2}
    assert [case.id for case in rank(choices)] == ["a", "b", "c", "z"]


@pytest.mark.parametrize(("source", "error"), [
    ("[", "cases.yml"),
    ("[]", "use_cases mapping"),
    ("use_cases: []", "nonempty list"),
    ("use_cases: [42]", "incorrect use case fields"),
])
def test_malformed_scorecard(tmp_path, source, error):
    path = tmp_path / "cases.yml"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_cases(path)


@pytest.mark.parametrize(("field", "value", "error"), [
    ("id", "../invalid", "invalid or duplicate"),
    ("title", " ", "single-line text"),
    ("title", "multiple\nlines", "single-line text"),
    ("impact", 6, "integer from 1 to 5"),
    ("risk", True, "integer from 1 to 5"),
    ("effort", 1.5, "integer from 1 to 5"),
])
def test_malformed_scorecard_rows(tmp_path, field, value, error):
    data = yaml.safe_load(SCORECARD.read_text(encoding="utf-8"))
    data["use_cases"][0][field] = value
    path = tmp_path / "cases.yml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_cases(path)


def test_duplicate_id_rejected(tmp_path):
    data = yaml.safe_load(SCORECARD.read_text(encoding="utf-8"))
    data["use_cases"][1]["id"] = data["use_cases"][0]["id"]
    path = tmp_path / "cases.yml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
