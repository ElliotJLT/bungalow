"""Turn a buyer's situation into a finished report by orchestrating the MCP.

This is the whole product in one function. Given what the buyer knows (price,
tenure, lease terms, title entries, survey findings), it calls the right MCP
tools, carries their answers through as findings, and assembles one report. It
adds no judgement of its own: the severities and actions are the MCP's words.
The value it adds is orchestration and aggregation, turning several tool calls
into a single prioritised document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .backend import ToolBackend
from .models import (
    BuyerType,
    DueDiligenceReport,
    Finding,
    Provider,
    Severity,
    StampDuty,
    Tenure,
)


@dataclass
class SurveyIssue:
    issue_type: str
    condition_rating: int = 2
    surveyor_notes: str = ""


@dataclass
class Situation:
    """Everything the buyer knows going in. Only the basics are required; the
    rest is filled in as their conveyancer sends documents."""

    postcode: str
    price: int
    buyer_type: BuyerType = "first_time_buyer"
    tenure: Tenure = "freehold"
    find_providers: bool = True

    # Lease (leasehold only)
    lease_remaining_years: int | None = None
    ground_rent_annual: int = 0
    ground_rent_escalation: str = "unknown"
    service_charge_annual: int = 0
    has_sinking_fund: bool = False
    share_of_freehold: bool = False
    lease_type: str = "flat"

    # Title register (optional)
    title_provided: bool = False
    title_class: str = "absolute"
    has_restrictive_covenants: bool = False
    has_easements: bool = False
    has_charges: bool = False
    charge_types: str = ""
    restrictions: str = ""
    proprietor_count: int = 1

    # Survey findings (optional)
    survey_issues: list[SurveyIssue] = field(default_factory=list)


def _findings_from_flags(source: str, payload: dict[str, Any]) -> list[Finding]:
    findings = []
    for flag in payload.get("flags", []):
        findings.append(
            Finding(
                source=source,
                issue=str(flag.get("issue", "")),
                severity=Severity.parse(str(flag.get("severity", "low"))),
                detail=str(flag.get("detail", "")),
                action=str(flag.get("action", "")),
            )
        )
    return findings


def _finding_from_survey(payload: dict[str, Any]) -> Finding:
    label = payload.get("condition_label", "")
    issue = payload.get("issue_type", "survey issue")
    rating = payload.get("condition_rating", "")
    detail_bits = [
        payload.get("plain_english", ""),
        f"Estimated cost: {payload.get('estimated_cost', 'unknown')}.",
        f"Specialist: {payload.get('specialist_needed', 'unknown')}.",
    ]
    insurance = payload.get("insurance_impact")
    if insurance:
        detail_bits.append(f"Insurance: {insurance}")
    return Finding(
        source="survey",
        issue=f"{issue} (condition {rating}): {label}",
        severity=Severity.parse(str(payload.get("urgency", "low"))),
        detail=" ".join(b for b in detail_bits if b),
        action=str(payload.get("recommendation", "")),
    )


def _stamp_duty(backend: ToolBackend, situation: Situation) -> StampDuty:
    payload = backend.call(
        "estimate_stamp_duty",
        {
            "purchase_price": situation.price,
            "first_time_buyer": situation.buyer_type == "first_time_buyer",
            "additional_property": situation.buyer_type == "additional_property",
        },
    )
    return StampDuty(
        total=int(payload["total_stamp_duty"]),
        effective_rate=float(payload.get("effective_rate_percent", 0.0)),
        buyer_type=str(payload.get("buyer_type", situation.buyer_type)),
        note=str(payload.get("note", "")),
    )


def _providers(backend: ToolBackend, situation: Situation) -> list[Provider]:
    payload = backend.call(
        "search_conveyancers",
        {"postcode": situation.postcode, "max_results": 5},
    )
    providers = [
        Provider(
            name=str(p.get("name", "")),
            status=str(p.get("status", "")),
            detail=str(p.get("trading_since", "") or ""),
        )
        for p in payload.get("providers", [])
    ]
    # Transparent ordering: currently authorised first. No hidden scoring.
    providers.sort(key=lambda p: p.status.lower() not in {"active", "authorised"})
    return providers


def build_report(situation: Situation, backend: ToolBackend) -> DueDiligenceReport:
    """Assemble the finished due-diligence pack for `situation`."""
    report = DueDiligenceReport(
        postcode=situation.postcode,
        price=situation.price,
        tenure=situation.tenure,
        buyer_type=situation.buyer_type,
        generated_at=datetime.now(timezone.utc),
    )

    report.stamp_duty = _stamp_duty(backend, situation)

    if situation.find_providers:
        report.providers = _providers(backend, situation)
        if not report.providers:
            report.notes.append(
                "Conveyancer register lookup returned nothing (the MCP's SRA and "
                "FCA lookups need API keys). Vet any firm on the SRA register and "
                "Companies House before instructing."
            )

    if situation.tenure == "leasehold" and situation.lease_remaining_years is not None:
        lease = backend.call(
            "check_lease_terms",
            {
                "remaining_years": situation.lease_remaining_years,
                "ground_rent_annual": situation.ground_rent_annual,
                "ground_rent_escalation": situation.ground_rent_escalation,
                "service_charge_annual": situation.service_charge_annual,
                "has_sinking_fund": situation.has_sinking_fund,
                "share_of_freehold": situation.share_of_freehold,
                "lease_type": situation.lease_type,
            },
        )
        report.findings.extend(_findings_from_flags("lease", lease))

    if situation.title_provided:
        title = backend.call(
            "parse_title_register",
            {
                "tenure": situation.tenure,
                "title_class": situation.title_class,
                "has_restrictive_covenants": situation.has_restrictive_covenants,
                "has_easements": situation.has_easements,
                "has_charges": situation.has_charges,
                "charge_types": situation.charge_types,
                "restrictions": situation.restrictions,
                "proprietor_count": situation.proprietor_count,
            },
        )
        report.findings.extend(_findings_from_flags("title", title))

    for issue in situation.survey_issues:
        survey = backend.call(
            "explain_survey_issue",
            {
                "issue_type": issue.issue_type,
                "condition_rating": issue.condition_rating,
                "surveyor_notes": issue.surveyor_notes,
            },
        )
        report.findings.append(_finding_from_survey(survey))

    return report
