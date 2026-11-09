import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

import yaml
from pydantic import ValidationError

from .domain import CATEGORIES, Category
from .triage import Triage, TriageRequest

FIELDS = ("request_id", "text", "expected")
SITES = ("Cedar site", "Birch site", "Alder site", "Maple site")


class LabeledRequest(TriageRequest):
    expected: Category


@dataclass(frozen=True)
class Failure:
    request_id: str
    text: str
    expected: str
    predicted: str
    confidence: float
    needs_review: bool


@dataclass(frozen=True)
class Evaluation:
    total: int
    correct: int
    accuracy_pct: float
    flagged: int
    unflagged_errors: int
    confusion: dict[str, dict[str, int]]
    failures: list[Failure]


def generate_benchmark(scenarios: Path, out: Path, seed: int) -> None:
    try:
        source = yaml.safe_load(scenarios.read_text(encoding="utf-8"))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{scenarios}: {exc}") from exc
    if not isinstance(source, dict) or set(source) != set(CATEGORIES):
        raise ValueError(f"{scenarios}: expected scenarios for each benchmark category")
    rng = Random(seed)
    examples = []
    for category in CATEGORIES:
        items = source[category]
        if not isinstance(items, list) or not items or not all(
            isinstance(item, str) and item.strip() for item in items
        ):
            raise ValueError(f"{scenarios}: {category} must contain a list of nonempty texts")
        examples.extend((f"{rng.choice(SITES)}: {item.strip()}", category) for item in items)
    rng.shuffle(examples)
    rows = [
        LabeledRequest(request_id=f"SYN-T{index:03d}", text=text, expected=expected)
        for index, (text, expected) in enumerate(examples, 1)
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(item.model_dump() for item in rows)


def read_benchmark(path: Path) -> list[LabeledRequest]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError(f"expected columns {', '.join(FIELDS)}")
            cases = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"line {reader.line_num}: wrong number of fields")
                try:
                    cases.append(LabeledRequest.model_validate(row))
                except ValidationError as exc:
                    raise ValueError(f"line {reader.line_num}: {exc}") from exc
        if not cases or len({case.request_id for case in cases}) != len(cases):
            raise ValueError("expected nonempty cases with unique request IDs")
        return cases
    except (ValueError, OSError, csv.Error) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def evaluate(cases: list[LabeledRequest], engine: Triage) -> Evaluation:
    if not cases:
        raise ValueError("evaluation requires at least one case")
    confusion = {label: dict.fromkeys(CATEGORIES, 0) for label in CATEGORIES}
    failures = []
    flagged = 0
    for case in cases:
        decision = engine.classify(case)
        confusion[case.expected][decision.category] += 1
        flagged += decision.needs_review
        if decision.category != case.expected:
            failures.append(Failure(case.request_id, case.text, case.expected, decision.category,
                                    decision.confidence, decision.needs_review))
    correct = len(cases) - len(failures)
    return Evaluation(
        len(cases), correct, 100 * correct / len(cases), flagged,
        sum(not failure.needs_review for failure in failures), confusion, failures,
    )


def safe_cell(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(
        "|", "&#124;"
    ).replace("\n", " ").replace("\r", " ")


def evaluation_report(result: Evaluation) -> str:
    lines = [
        "# Synthetic triage benchmark", "",
        "The deterministic mock was evaluated offline. Exact category matches count as correct. "
        "Cases sent to review still count in the denominator.", "",
        f"- Accuracy: **{result.correct}/{result.total} ({result.accuracy_pct:.2f}%)**.",
        f"- Flagged for review: {result.flagged}/{result.total}.",
        f"- Incorrect categories without a review flag: {result.unflagged_errors}.", "",
        "## Confusion matrix", "",
        "| Expected / predicted | " + " | ".join(CATEGORIES) + " |",
        "| --- | " + " | ".join("---:" for _ in CATEGORIES) + " |",
    ]
    for expected, counts in result.confusion.items():
        lines.append(f"| {expected} | " + " | ".join(str(counts[label]) for label in CATEGORIES)
                     + " |")
    lines.extend([
        "", "## Every incorrect category", "",
        "| Request | Expected | Predicted | Score | Review | Synthetic request text |",
        "| --- | --- | --- | ---: | --- | --- |",
    ])
    for item in result.failures:
        lines.append(
            f"| {item.request_id} | {item.expected} | {item.predicted} | {item.confidence:.2f} | "
            f"{'yes' if item.needs_review else 'no'} | {safe_cell(item.text)} |"
        )
    lines.extend([
        "", "Scores are heuristic. Template coverage and failure frequencies are properties "
        "of this synthetic benchmark.", "",
    ])
    return "\n".join(lines)


def write_evaluation(out: Path, result: Evaluation) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "triage-evaluation.json").write_text(
        json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8",
    )
    (out / "triage-evaluation.md").write_text(evaluation_report(result), encoding="utf-8")
