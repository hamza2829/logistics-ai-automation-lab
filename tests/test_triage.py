import pytest
from fastapi.testclient import TestClient

from logistics_lab.api import app, create_app
from logistics_lab.triage import MockLLM, ProviderUnavailable, Triage, TriageRequest

MOCK = Triage(MockLLM())


@pytest.mark.parametrize(("text", "category"), [
    ("Trace a parcel in the mailroom.", "mail_parcel"),
    ("Please revise the ROUTE SHEET before lunch.", "dispatch"),
    ("Can you book a driver for the morning?", "driver_booking"),
    ("Confirm the SKU and the bin location.", "warehouse_order"),
])
def test_mock_categories_and_determinism(text, category):
    request = TriageRequest(request_id="SYN-42", text=text)
    result = MOCK.classify(request)
    assert result == MOCK.classify(request)
    assert result.category == category
    assert result.engine == "mock"
    assert 0.75 <= result.confidence <= 1
    assert not result.needs_review


@pytest.mark.parametrize(("text", "category", "score"), [
    ("Help with yesterday's item.", "other", 0.2),
    ("The word dispatching contains a dispatch-like stem.".replace("dispatch-like", "similar"),
     "other", 0.2),
    ("A parcel and a route sheet were left on the desk.", "mail_parcel", 0.48),
    ("The route sheet mentions dispatch and a parcel.", "dispatch", 0.66),
])
def test_low_confidence_and_ambiguous_requests_are_flagged(text, category, score):
    result = MOCK.classify(TriageRequest(request_id="SYN-42", text=text))
    assert (result.category, result.confidence, result.needs_review) == (category, score, True)


@pytest.mark.parametrize("provider_result", [
    ProviderUnavailable("offline"), TimeoutError("elapsed"), {"category": "bogus", "confidence": 1},
    {"category": "dispatch", "confidence": 1.01}, {"category": "dispatch", "confidence": float("nan")},
])
def test_bad_provider_uses_conservative_rules_fallback(provider_result):
    class Adapter:
        def classify(self, _text):
            if isinstance(provider_result, Exception):
                raise provider_result
            return provider_result

    result = Triage(Adapter(), "test-adapter").classify(
        TriageRequest(request_id="SYN-7", text="Please find a driver."),
    )
    assert (result.category, result.confidence, result.engine, result.needs_review) == (
        "driver_booking", 0.55, "rules", True,
    )


@pytest.mark.parametrize("text", ["None of the phrases match.", "Find the driver with the parcel."])
def test_rules_return_other_on_no_match_or_tie(text):
    result = Triage(None).classify(TriageRequest(request_id="SYN-42", text=text))
    assert result.category == "other"
    assert result.needs_review and result.engine == "rules"


def test_adapter_result_is_validated_and_other_requires_review():
    class Adapter:
        def classify(self, _text):
            return {"category": "other", "confidence": 1}

    client = TestClient(create_app(Triage(Adapter(), "custom")))
    result = client.post("/triage", json={"request_id": "X1", "text": "Hello"}).json()
    assert result == {
        "request_id": "X1", "category": "other", "confidence": 1,
        "engine": "custom", "needs_review": True,
    }


@pytest.mark.parametrize("payload", [
    {}, {"request_id": "X1"}, {"request_id": "X1", "text": " "},
    {"request_id": "bad id", "text": "parcel"}, {"request_id": "X" * 65, "text": "parcel"},
    {"request_id": "X1", "text": "a" * 501}, {"request_id": "X1", "text": 123},
    {"request_id": "X1", "text": "parcel", "expected": "mail_parcel"},
])
def test_api_rejects_invalid_payloads(payload):
    with TestClient(app) as client:
        assert client.post("/triage", json=payload).status_code == 422


def test_api_contract_and_health():
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        response = client.post("/triage", json={"request_id": " X1 ", "text": " SKU issue "})
        assert response.status_code == 200
        assert response.json() == {
            "request_id": "X1", "category": "warehouse_order", "confidence": 0.86,
            "needs_review": False, "engine": "mock",
        }
