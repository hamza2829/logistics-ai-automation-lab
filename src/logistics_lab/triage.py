import re
from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .domain import Category

REVIEW_THRESHOLD = 0.75
REQUEST_ID = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: str = Field(pattern=REQUEST_ID)
    text: str = Field(min_length=1, max_length=500)


class Prediction(BaseModel):
    category: Category
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


class Decision(Prediction):
    request_id: str
    needs_review: bool
    engine: str


class ProviderUnavailable(Exception):
    """An adapter can raise this to signal a recoverable failure."""


class LLM(Protocol):
    def classify(self, text: str) -> Prediction | Mapping[str, object]: ...


MOCK_PHRASES: dict[Category, tuple[str, ...]] = {
    "mail_parcel": ("parcel", "mailroom", "mail tray", "postage", "courier envelope", "mail bag"),
    "dispatch": ("dispatch", "route sheet", "vehicle allocation", "outbound route", "load plan"),
    "driver_booking": ("driver booking", "book a driver", "driver shift", "driver availability",
                       "substitute driver", "reserve a driver"),
    "warehouse_order": ("warehouse order", "pick list", "picking", "stock transfer", "sku",
                        "replenishment", "bin location"),
}
RULE_PHRASES: dict[Category, tuple[str, ...]] = {
    "mail_parcel": ("parcel", "envelope", "mailroom"),
    "dispatch": ("dispatch", "route", "vehicle"),
    "driver_booking": ("driver", "shift"),
    "warehouse_order": ("warehouse", "stock", "sku"),
}


def phrase_scores(text: str, vocabulary: dict[Category, tuple[str, ...]]) -> list[tuple[int, Category]]:
    ranked = [
        (sum(bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE))
             for phrase in phrases), category)
        for category, phrases in vocabulary.items()
    ]
    return sorted(ranked, key=lambda match: -match[0])


class MockLLM:
    """A deterministic phrase matcher behind the same interface as a provider."""

    def classify(self, text: str) -> Prediction:
        (best, category), (second, _), *_ = phrase_scores(text, MOCK_PHRASES)
        if best == 0:
            return Prediction(category="other", confidence=0.2)
        if best == second:
            return Prediction(category=category, confidence=0.48)
        if second:
            return Prediction(category=category, confidence=0.66)
        return Prediction(category=category, confidence=round(min(0.98, 0.86 + 0.04 * (best - 1)), 2))


def fallback(text: str) -> Prediction:
    (best, category), (second, _), *_ = phrase_scores(text, RULE_PHRASES)
    if not best or best == second:
        return Prediction(category="other", confidence=0.2)
    return Prediction(category=category, confidence=0.55)


class Triage:
    def __init__(self, provider: LLM | None, engine_name: str = "mock") -> None:
        self.provider = provider
        self.engine_name = engine_name

    def classify(self, request: TriageRequest) -> Decision:
        prediction = None
        if self.provider is not None:
            try:
                prediction = Prediction.model_validate(self.provider.classify(request.text))
            except (ProviderUnavailable, TimeoutError, ValidationError):
                pass
        engine = self.engine_name
        if prediction is None:
            prediction = fallback(request.text)
            engine = "rules"
        return Decision(
            **prediction.model_dump(), request_id=request.request_id, engine=engine,
            needs_review=prediction.category == "other" or prediction.confidence < REVIEW_THRESHOLD,
        )
