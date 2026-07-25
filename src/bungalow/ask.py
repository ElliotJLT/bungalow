"""The natural-language front door.

Instead of remembering flags, you describe the property in plain English and
bungalow works out the rest:

    bungalow ask "first-time buyer, 450k leasehold flat in Hackney, 90 years
                  left, 300 a year ground rent that doubles"

Claude reads that into the structured fields the engine already takes, then the
engine runs and you get the pack. If the one thing it cannot do without is
missing (the asking price), it asks for that rather than guessing. This is the
openworker shape: a plain request in, finished work out, a question before it
assumes anything that would change the answer.

Extraction needs an Anthropic key at run time. The engine still needs the
homebuyer-mcp for the live tools. Both are injectable so the flow is tested
without either.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .backend import ToolBackend
from .builder import Situation, SurveyIssue, build_report
from .listing import ListingFields, build_triage
from .models import DueDiligenceReport

DEFAULT_MODEL = "claude-sonnet-4-6"

_SURVEY_TYPES = [
    "subsidence",
    "rising_damp",
    "penetrating_damp",
    "dry_rot",
    "wet_rot",
    "woodworm",
    "asbestos",
    "japanese_knotweed",
    "roof_defects",
    "electrical",
]

_SYSTEM = """\
You read a UK home-buyer's plain-English description of a property they are \
considering and extract the structured facts. Use 0 for any number not given and \
"unknown" for any unknown enum. Do not invent figures. If the buyer does not say \
whether they are a first-time buyer, assume first_time_buyer. Only fill \
survey_issues if the buyer actually describes a survey finding.

Set clarifying_question to a single short question only when you cannot produce a \
useful answer without it. The one fact you truly need is the asking price; if it \
is missing, ask for it. Otherwise leave clarifying_question empty. Do not ask for \
things that only refine the answer (the buyer can add them later).\
"""


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "price": {"type": "integer", "description": "Asking price in GBP, 0 if not given."},
            "postcode": {"type": "string", "description": "Postcode or area, empty if not given."},
            "tenure": {"type": "string", "enum": ["freehold", "leasehold", "unknown"]},
            "buyer_type": {
                "type": "string",
                "enum": ["first_time_buyer", "home_mover", "additional_property"],
            },
            "lease_years": {"type": "integer", "description": "Years left on lease, 0 if n/a."},
            "ground_rent_annual": {"type": "integer", "description": "Ground rent/yr, 0 if none"},
            "ground_rent_escalation": {
                "type": "string",
                "enum": ["none", "fixed", "rpi", "doubling", "unknown"],
            },
            "service_charge_annual": {"type": "integer"},
            "survey_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_type": {"type": "string", "enum": _SURVEY_TYPES},
                        "condition_rating": {"type": "integer", "enum": [1, 2, 3]},
                    },
                    "required": ["issue_type", "condition_rating"],
                    "additionalProperties": False,
                },
            },
            "clarifying_question": {"type": "string"},
        },
        "required": [
            "price",
            "postcode",
            "tenure",
            "buyer_type",
            "lease_years",
            "ground_rent_annual",
            "ground_rent_escalation",
            "service_charge_annual",
            "survey_issues",
            "clarifying_question",
        ],
        "additionalProperties": False,
    }


@dataclass
class Extraction:
    price: int = 0
    postcode: str = ""
    tenure: str = "unknown"
    buyer_type: str = "first_time_buyer"
    lease_years: int = 0
    ground_rent_annual: int = 0
    ground_rent_escalation: str = "unknown"
    service_charge_annual: int = 0
    survey_issues: list[SurveyIssue] = field(default_factory=list)
    clarifying_question: str = ""

    @property
    def needs_more(self) -> bool:
        return self.price <= 0 or bool(self.clarifying_question.strip())

    @property
    def question(self) -> str:
        return self.clarifying_question.strip() or "What is the asking price?"


def extract(text: str, *, client: Any | None = None, model: str = DEFAULT_MODEL) -> Extraction:
    """Turn a plain-English description into structured fields via Claude."""
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=600,
        temperature=0.0,
        system=_SYSTEM,
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": _schema()}},
    )
    blocks = response.content
    payload = next(
        (getattr(b, "text", "") for b in blocks if getattr(b, "type", None) == "text"), ""
    )
    raw = json.loads(payload)
    return Extraction(
        price=int(raw.get("price", 0)),
        postcode=str(raw.get("postcode", "")),
        tenure=str(raw.get("tenure", "unknown")),
        buyer_type=str(raw.get("buyer_type", "first_time_buyer")),
        lease_years=int(raw.get("lease_years", 0)),
        ground_rent_annual=int(raw.get("ground_rent_annual", 0)),
        ground_rent_escalation=str(raw.get("ground_rent_escalation", "unknown")),
        service_charge_annual=int(raw.get("service_charge_annual", 0)),
        survey_issues=[
            SurveyIssue(
                issue_type=str(s["issue_type"]),
                condition_rating=int(s.get("condition_rating", 2)),
            )
            for s in raw.get("survey_issues", [])
        ],
        clarifying_question=str(raw.get("clarifying_question", "")),
    )


def _to_listing(ex: Extraction) -> ListingFields:
    tenure = ex.tenure if ex.tenure in ("freehold", "leasehold") else "freehold"
    return ListingFields(
        price=ex.price,
        postcode=ex.postcode,
        tenure=tenure,
        lease_years=ex.lease_years or None,
        ground_rent_annual=ex.ground_rent_annual,
        ground_rent_escalation=ex.ground_rent_escalation,
        service_charge_annual=ex.service_charge_annual,
    )


def run_ask(
    text: str,
    *,
    extract_client: Any | None = None,
    backend: ToolBackend | None = None,
    model: str = DEFAULT_MODEL,
) -> tuple[DueDiligenceReport | None, str | None]:
    """Extract, then run the engine. Returns (report, None) or (None, question)."""
    ex = extract(text, client=extract_client, model=model)
    if ex.needs_more:
        return None, ex.question

    if backend is None:
        from .backend import MCPBackend

        backend = MCPBackend()

    # A survey finding means the buyer is past browse-time, so run the full pack.
    if ex.survey_issues:
        tenure = ex.tenure if ex.tenure in ("freehold", "leasehold") else "freehold"
        situation = Situation(
            postcode=ex.postcode,
            price=ex.price,
            buyer_type=ex.buyer_type,  # type: ignore[arg-type]
            tenure=tenure,  # type: ignore[arg-type]
            find_providers=False,
            lease_remaining_years=ex.lease_years or None,
            ground_rent_annual=ex.ground_rent_annual,
            ground_rent_escalation=ex.ground_rent_escalation,
            service_charge_annual=ex.service_charge_annual,
            survey_issues=ex.survey_issues,
        )
        return build_report(situation, backend), None

    return build_triage(_to_listing(ex), backend, ex.buyer_type), None  # type: ignore[arg-type]
