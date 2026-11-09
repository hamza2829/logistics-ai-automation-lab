import csv
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random

from .domain import PRIORITIES, REQUEST_TYPES

FIELDS = ("request_id", "sequence", "timestamp", "request_type", "priority", "activity", "status")
STATUS = {
    "received": "new",
    "triage": "classified",
    "queue": "waiting",
    "process": "in_progress",
    "quality_check": "checking",
    "rework": "needs_rework",
    "completed": "closed",
}
EDGES = {
    ("received", "triage"), ("triage", "queue"), ("queue", "process"),
    ("process", "quality_check"), ("quality_check", "completed"),
    ("quality_check", "rework"), ("rework", "queue"),
}
START = datetime(2025, 2, 3, 8, tzinfo=UTC)
# Queue windows and rework chances are simulation inputs, not measured values.
PROFILES = {
    "mail_parcel": (15, 75, 0.08),
    "dispatch": (25, 120, 0.13),
    "driver_booking": (45, 210, 0.17),
    "warehouse_order": (60, 270, 0.23),
}


def event_rows(count: int, seed: int) -> Iterator[tuple]:
    if count < 1:
        raise ValueError("request count must be positive")
    rng = Random(seed)
    for number in range(1, count + 1):
        request_id = f"SYN-{number:06d}"
        request_type = rng.choices(REQUEST_TYPES, weights=(30, 26, 18, 26))[0]
        priority = rng.choices(PRIORITIES, weights=(12, 60, 22, 6))[0]
        queue_low, queue_high, rework_chance = PROFILES[request_type]
        queue_multiplier = {"low": 1.4, "normal": 1, "high": 0.65, "urgent": 0.35}[priority]
        started = START + timedelta(
            days=rng.randrange(6) * 7 + rng.randrange(5), minutes=rng.randrange(9 * 60),
        )
        # Dwell time belongs to the activity entered, up to the next timestamp.
        steps = [("received", rng.randint(2, 18)), ("triage", rng.randint(4, 22))]
        for attempt in range(3):
            steps.extend([
                ("queue", max(1, round(rng.randint(queue_low, queue_high) * queue_multiplier))),
                ("process", rng.randint(10, 65)),
                ("quality_check", rng.randint(3, 17)),
            ])
            if attempt == 2 or rng.random() >= rework_chance:
                break
            steps.append(("rework", rng.randint(15, 85)))
        steps.append(("completed", 0))

        timestamp = started
        for sequence, (activity, dwell) in enumerate(steps, 1):
            yield (request_id, sequence, timestamp.isoformat(), request_type, priority, activity,
                   STATUS[activity])
            timestamp += timedelta(minutes=dwell)


def generate_events(path: Path, count: int = 3000, seed: int = 2829) -> None:
    if count < 1:
        raise ValueError("request count must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(event_rows(count, seed))
