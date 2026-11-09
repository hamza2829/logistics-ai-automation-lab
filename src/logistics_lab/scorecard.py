import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class UseCase:
    id: str
    title: str
    area: str
    impact: int
    effort: int
    risk: int
    hypothesis: str
    measure: str
    boundary: str

    @property
    def score(self) -> int:
        return 2 * self.impact - self.effort - 2 * self.risk


TEXT_FIELDS = ("id", "title", "area", "hypothesis", "measure", "boundary")
SCORED_FIELDS = ("impact", "effort", "risk")


def load_cases(path: Path) -> list[UseCase]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(document, dict) or set(document) != {"use_cases"}:
        raise ValueError(f"{path}: expected a use_cases mapping")
    rows = document["use_cases"]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: expected a nonempty list of use cases")
    seen = set()
    cases = []
    for index, row in enumerate(rows, 1):
        context = f"{path}: entry {index}"
        if not isinstance(row, dict) or set(row) != set(TEXT_FIELDS + SCORED_FIELDS):
            raise ValueError(f"{context}: incorrect use case fields")
        for key in TEXT_FIELDS:
            if not isinstance(row[key], str) or not row[key].strip() or not row[key].isprintable():
                raise ValueError(f"{context}: {key} must be single-line text")
            row[key] = row[key].strip()
        for key in SCORED_FIELDS:
            if type(row[key]) is not int or not 1 <= row[key] <= 5:
                raise ValueError(f"{context}: {key} must be an integer from 1 to 5")
        case = UseCase(**row)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case.id) or case.id in seen:
            raise ValueError(f"{context}: invalid or duplicate use case ID")
        seen.add(case.id)
        cases.append(case)
    return cases


def rank(cases: list[UseCase]) -> list[UseCase]:
    return sorted(cases, key=lambda case: (-case.score, case.risk, case.effort, case.id))


def md(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("|", "&#124;"))


def scorecard(cases: list[UseCase]) -> str:
    ranked = rank(cases)
    lines = [
        "# Logistics AI use case scorecard", "",
        "Scores are workshop assumptions for a fictional service. A 1 is low and a 5 is high.",
        "Rank by `2 × impact - effort - 2 × risk`. Break ties by lower risk, then lower effort, "
        "then case ID. A risk score of 4 or 5 triggers a hold for human assessment.", "",
        "| Rank | Candidate | Service area | Impact | Effort | Risk | Score | Decision |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for position, case in enumerate(ranked, 1):
        decision = "Hold for assessment" if case.risk >= 4 else "Candidate for experiment"
        lines.append(f"| {position} | {md(case.title)} | {md(case.area)} | {case.impact} | "
                     f"{case.effort} | {case.risk} | {case.score} | {decision} |")
    for case in ranked:
        lines.extend([
            "", f"## {md(case.title)}", "",
            f"- Hypothesis: {md(case.hypothesis)}",
            f"- Measure: {md(case.measure)}",
            f"- Boundary: {md(case.boundary)}",
        ])
    return "\n".join(lines) + "\n"


def write_scorecard(source: Path, out: Path) -> None:
    content = scorecard(load_cases(source))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
