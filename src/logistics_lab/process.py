import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .domain import PRIORITIES, REQUEST_TYPES
from .events import EDGES, FIELDS, STATUS


@dataclass(frozen=True)
class Summary:
    requests: int
    events: int
    completed: int
    reworked: int
    rework_events: int
    rework_rate_pct: float
    median_completed_minutes: float | None


@dataclass
class Analysis:
    summary: Summary
    steps: pd.DataFrame
    edges: pd.DataFrame
    by_type: pd.DataFrame


def read_event_log(path: Path) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, ValueError, OSError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if set(frame.columns) != set(FIELDS) or not isinstance(frame.index, pd.RangeIndex):
        raise ValueError(f"{path}: expected columns {', '.join(FIELDS)}")
    if frame.empty:
        raise ValueError(f"{path}: event log is empty")
    if not frame["request_id"].str.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}").all():
        raise ValueError(f"{path}: invalid request ID")
    if not frame["sequence"].str.fullmatch(r"[1-9][0-9]{0,8}").all():
        raise ValueError(f"{path}: sequence must contain positive integers")
    frame["sequence"] = frame["sequence"].astype(int)
    valid_zones = frame["timestamp"].str.contains(r"(?:Z|[+-][0-9]{2}:[0-9]{2})$", regex=True)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="ISO8601", utc=True, errors="coerce")
    if not valid_zones.all() or frame["timestamp"].isna().any():
        raise ValueError(f"{path}: timestamps must be ISO 8601 with a timezone")
    if not frame["request_type"].isin(REQUEST_TYPES).all() or not frame["priority"].isin(
        PRIORITIES
    ).all():
        raise ValueError(f"{path}: invalid request type or priority")
    if not frame["activity"].map(STATUS).eq(frame["status"]).all():
        raise ValueError(f"{path}: invalid activity or status")

    frame = frame.sort_values(["request_id", "sequence"]).reset_index(drop=True)
    cases = frame.groupby("request_id", sort=False)
    if not frame["sequence"].eq(cases.cumcount() + 1).all():
        raise ValueError(f"{path}: sequence must start at one and increase by one per request")
    if cases["timestamp"].diff().le(pd.Timedelta(0)).any():
        raise ValueError(f"{path}: timestamps must increase within each request")
    if cases[["request_type", "priority"]].nunique().gt(1).any().any():
        raise ValueError(f"{path}: request type and priority must stay constant")
    if not cases["activity"].first().eq("received").all():
        raise ValueError(f"{path}: each request must start at received")
    next_activity = cases["activity"].shift(-1)
    follows = next_activity.notna()
    observed = set(zip(frame.loc[follows, "activity"], next_activity[follows], strict=True))
    if observed - EDGES:
        raise ValueError(f"{path}: invalid transition {sorted(observed - EDGES)[0]}")
    return frame


def analyze(frame: pd.DataFrame) -> Analysis:
    cases = frame.groupby("request_id", sort=False)
    frame = frame.assign(
        next_activity=cases["activity"].shift(-1),
        minutes=(cases["timestamp"].shift(-1) - frame["timestamp"]).dt.total_seconds() / 60,
    )
    measured = frame[frame["next_activity"].notna()]
    steps = measured.groupby("activity")["minutes"].agg(
        samples="size", median_minutes="median", p90_minutes=lambda values: values.quantile(0.9),
        total_minutes="sum",
    ).reset_index().sort_values(["p90_minutes", "activity"], ascending=[False, True])
    edges = measured.groupby(["activity", "next_activity"]).size().reset_index(name="count")

    rework = frame["activity"].eq("rework")
    rework_by_case = rework.groupby(frame["request_id"], sort=False).any()
    case_rows = cases.agg(
        request_type=("request_type", "first"), start=("timestamp", "first"),
        end=("timestamp", "last"), last=("activity", "last"),
    ).assign(reworked=rework_by_case)
    case_rows["completed"] = case_rows["last"].eq("completed")
    case_rows["cycle_minutes"] = (
        (case_rows["end"] - case_rows["start"]).dt.total_seconds() / 60
    ).where(case_rows["completed"])
    by_type = case_rows.groupby("request_type").agg(
        requests=("completed", "size"), completed=("completed", "sum"),
        reworked=("reworked", "sum"), median_completed_minutes=("cycle_minutes", "median"),
    ).reset_index()
    completed = int(case_rows["completed"].sum())
    reworked = int(case_rows["reworked"].sum())
    summary = Summary(
        len(case_rows), len(frame), completed, reworked, int(rework.sum()),
        100 * reworked / len(case_rows),
        float(case_rows["cycle_minutes"].median()) if completed else None,
    )
    return Analysis(summary, steps, edges, by_type)


def chart(steps: pd.DataFrame, path: Path) -> None:
    figure = Figure(figsize=(8, 4.2), layout="constrained", facecolor="white")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    if steps.empty:
        axis.text(0.5, 0.5, "No observed step intervals", ha="center", va="center")
        axis.set_axis_off()
    else:
        positions = list(range(len(steps)))
        axis.barh([pos - 0.18 for pos in positions], steps["p90_minutes"], 0.34,
                  color="#256685", label="90th percentile")
        axis.barh([pos + 0.18 for pos in positions], steps["median_minutes"], 0.34,
                  color="#11a08a", label="Median")
        axis.set_yticks(positions, [name.replace("_", " ") for name in steps["activity"]])
        axis.invert_yaxis()
        axis.set_xlabel("Elapsed minutes to the next event")
        axis.legend(loc="lower right")
        axis.grid(axis="x", alpha=0.22)
        axis.set_axisbelow(True)
    axis.set_title("Synthetic logistics | Step dwell times", loc="left", fontweight="bold")
    figure.savefig(path, dpi=150)


def report(analysis: Analysis) -> str:
    summary = analysis.summary
    median = (f"{summary.median_completed_minutes:.1f} min"
              if summary.median_completed_minutes is not None else "Unavailable")
    lines = [
        "# Synthetic logistics process report", "",
        f"- Requests observed: {summary.requests:,} across {summary.events:,} events.",
        f"- Completed requests: {summary.completed:,}. Median completed cycle: {median}.",
        f"- Rework: {summary.reworked:,} requests ({summary.rework_rate_pct:.2f}%) with "
        f"{summary.rework_events:,} rework visits.", "",
        "Step dwell is elapsed time from a step's entry to the next event in the same request. "
        "The last event has no measured interval. Request cycle time uses completed traces only.",
        "", "## Bottlenecks by 90th percentile dwell", "",
        "![Median and p90 dwell in minutes by activity](step-times.png)", "",
        "| Step | Intervals | Median min | P90 min | Total min |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in analysis.steps.itertuples(index=False):
        lines.append(f"| {row.activity} | {row.samples:,} | {row.median_minutes:.1f} | "
                     f"{row.p90_minutes:.1f} | {row.total_minutes:.1f} |")
    lines.extend(["", "## Directly follows graph", ""])
    if analysis.edges.empty:
        lines.append("No observed transitions.")
    else:
        lines.extend(["```mermaid", "flowchart LR"])
        for row in analysis.edges.itertuples(index=False):
            lines.append(f"    {row.activity} -->|{row.count}| {row.next_activity}")
        lines.append("```")
    lines.extend([
        "", "Edge labels count adjacent events within requests. Repeated visits count separately.",
        "The simulated bottlenecks reflect generator assumptions.", "",
    ])
    return "\n".join(lines)


def write_analysis(out: Path, analysis: Analysis) -> None:
    out.mkdir(parents=True, exist_ok=True)
    analysis.steps.to_csv(out / "step-times.csv", index=False)
    analysis.edges.to_csv(out / "directly-follows.csv", index=False)
    analysis.by_type.to_csv(out / "requests-by-type.csv", index=False)
    chart(analysis.steps, out / "step-times.png")
    (out / "summary.json").write_text(
        json.dumps(asdict(analysis.summary), indent=2) + "\n", encoding="utf-8",
    )
    (out / "process-report.md").write_text(report(analysis), encoding="utf-8")
