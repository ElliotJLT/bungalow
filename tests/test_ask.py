from __future__ import annotations

import json

from bungalow._sample_data import SAMPLE_RESPONSES
from bungalow.ask import extract, run_ask
from bungalow.backend import StaticBackend


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Resp:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]


class _FakeClient:
    """Returns a fixed extraction payload, capturing the request."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls: list[dict[str, object]] = []

    @property
    def messages(self):  # type: ignore[no-untyped-def]
        return self

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return _Resp(json.dumps(self._payload))


_FULL = {
    "price": 475000,
    "postcode": "SE22 8HR",
    "tenure": "leasehold",
    "buyer_type": "first_time_buyer",
    "lease_years": 82,
    "ground_rent_annual": 250,
    "ground_rent_escalation": "doubling",
    "service_charge_annual": 1800,
    "survey_issues": [],
    "clarifying_question": "",
}


def _clone(**overrides: object) -> dict[str, object]:
    return {**_FULL, **overrides}


def test_extract_maps_fields() -> None:
    ex = extract("450k leasehold flat", client=_FakeClient(_FULL))
    assert ex.price == 475000
    assert ex.tenure == "leasehold"
    assert ex.lease_years == 82
    assert ex.ground_rent_escalation == "doubling"
    assert ex.needs_more is False


def test_ask_produces_a_pack_from_plain_english() -> None:
    report, question = run_ask(
        "first-time buyer, 475k leasehold flat in SE22, 82 years left, 250 ground rent doubling",
        extract_client=_FakeClient(_FULL),
        backend=StaticBackend(SAMPLE_RESPONSES),
    )
    assert question is None
    assert report is not None
    assert report.stamp_duty is not None
    assert any("ground rent" in f.issue.lower() for f in report.findings)


def test_ask_asks_for_price_when_missing() -> None:
    report, question = run_ask(
        "leasehold flat in SE22",
        extract_client=_FakeClient(_clone(price=0)),
        backend=StaticBackend(SAMPLE_RESPONSES),
    )
    assert report is None
    assert question and "price" in question.lower()


def test_ask_uses_a_clarifying_question_from_the_model() -> None:
    report, question = run_ask(
        "a flat somewhere",
        extract_client=_FakeClient(_clone(price=0, clarifying_question="Which town or postcode?")),
        backend=StaticBackend(SAMPLE_RESPONSES),
    )
    assert report is None
    assert question == "Which town or postcode?"


def test_ask_runs_full_pack_when_a_survey_issue_is_mentioned() -> None:
    payload = _clone(survey_issues=[{"issue_type": "subsidence", "condition_rating": 3}])
    report, question = run_ask(
        "475k leasehold flat SE22, survey found subsidence",
        extract_client=_FakeClient(payload),
        backend=StaticBackend(SAMPLE_RESPONSES),
    )
    assert question is None
    assert report is not None
    assert any(f.source == "survey" for f in report.findings)


def test_extract_request_uses_structured_output() -> None:
    client = _FakeClient(_FULL)
    extract("anything", client=client)
    sent = client.calls[0]
    assert sent["output_config"]["format"]["type"] == "json_schema"  # type: ignore[index]
    assert sent["temperature"] == 0.0
