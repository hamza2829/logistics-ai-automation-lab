"""Exercise the published webhook and approval callback on an isolated runner."""

import json
from time import sleep
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

INTAKE = "http://127.0.0.1:5678/webhook/logistics-triage"


def post(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(url, data=json.dumps(payload).encode(), method="POST",
                      headers={"Content-Type": "application/json"})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def record(name: str, status: int, result: dict) -> None:
    public = {key: result[key] for key in
              ("request_id", "category", "confidence", "needs_review", "engine", "route", "error")
              if key in result}
    print(f"{name} HTTP {status} {json.dumps(public, sort_keys=True)}")


def review(decision: str) -> None:
    request_id = f"SYN-CI-{decision.upper()}"
    status, result = post(INTAKE, {
        "request_id": request_id, "text": "Please help with the item from yesterday.",
    })
    record(f"{decision} intake", status, result)
    assert status == 202
    assert (result["request_id"], result["route"], result["needs_review"]) == (
        request_id, "pending_review", True,
    )
    url = result["review_url"]
    parsed = urlsplit(url)
    assert parsed.scheme == "http" and parsed.netloc == "127.0.0.1:5678"
    assert parsed.path.startswith("/webhook-waiting/")
    for _ in range(20):
        status, result = post(url, {"decision": decision})
        if status != 404:
            break
        sleep(0.25)
    record(f"{decision} callback", status, result)
    assert status == 200
    expected = "approved" if decision == "approve" else "rejected"
    assert result == {"request_id": request_id, "category": "other", "route": expected}


def main() -> None:
    status, result = post(INTAKE, {"request_id": "bad id", "text": ""})
    record("invalid intake", status, result)
    assert status == 422 and "error" in result

    status, result = post(INTAKE, {
        "request_id": "SYN-CI-AUTO", "text": "The mailroom needs help tracing a parcel.",
    })
    record("automatic intake", status, result)
    assert status == 200
    assert (result["category"], result["route"], result["engine"]) == (
        "mail_parcel", "automatic", "mock",
    )
    assert result["needs_review"] is False

    review("approve")
    review("reject")
    print("PASS: validation, offline triage, approval and rejection completed.")


if __name__ == "__main__":
    main()
