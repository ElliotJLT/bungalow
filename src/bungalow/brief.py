"""The optional plain-English brief, written by Claude.

The builder produces the facts; this turns them into the two or three sentences a
stressed buyer actually reads first. Claude is given only the findings the MCP
returned and told to summarise them, not add to them. If there is no key or the
call fails, the report is fine without a brief.
"""

from __future__ import annotations

from typing import Any

from .models import DueDiligenceReport

DEFAULT_MODEL = "claude-sonnet-4-6"

_SYSTEM = """\
You are writing the opening of a UK home-buyer's due-diligence pack. You are given \
a list of findings that were produced by regulated-data tools. Write two to four \
short sentences, plain and calm, that tell the buyer what matters most and what to \
do first. Lead with the single most serious issue. Do not invent any fact, figure, \
or reassurance that is not in the findings. Do not give legal or financial advice. \
No preamble, just the summary.\
"""


def write_brief(
    report: DueDiligenceReport,
    *,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Return a short brief for `report`, or an empty string on any failure."""
    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=300,
            temperature=0.0,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _facts(report)}],
        )
        blocks = response.content
        text = next(
            (getattr(b, "text", "") for b in blocks if getattr(b, "type", None) == "text"),
            "",
        )
        return str(text).strip()
    except Exception:  # noqa: BLE001 - the brief is optional, never break the report
        return ""


def deterministic_brief(report: DueDiligenceReport) -> str:
    """A plain summary composed from the findings, no model needed.

    Restates what the MCP flagged; it is the default brief and the fallback when
    no key is present. It adds no judgement beyond counting and ordering.
    """
    if not report.findings:
        return (
            "Nothing was flagged on what was checked. Add lease, title, and survey "
            "details for a fuller picture."
        )
    from .models import Severity

    top = report.sorted_findings()[0]
    highs = sum(1 for f in report.findings if f.severity is Severity.HIGH)
    mediums = sum(1 for f in report.findings if f.severity is Severity.MEDIUM)
    parts = [f"The most serious item is {top.issue.lower()} (from the {top.source})."]
    if highs:
        parts.append(
            f"{highs} high and {mediums} medium concern(s) in total. "
            "Resolve the high-severity items before spending on surveys or legal work."
        )
    else:
        parts.append(f"{mediums} medium concern(s) and nothing high-severity on what was checked.")
    return " ".join(parts)


def _facts(report: DueDiligenceReport) -> str:
    lines = [
        f"Property: {report.postcode}, £{report.price:,}, {report.tenure}, "
        f"{report.buyer_type.replace('_', ' ')}.",
    ]
    if report.stamp_duty:
        lines.append(f"Stamp duty: £{report.stamp_duty.total:,}.")
    if report.findings:
        lines.append("Findings:")
        for f in report.sorted_findings():
            lines.append(f"- [{f.severity}] ({f.source}) {f.issue}: {f.detail} Action: {f.action}")
    else:
        lines.append("No property findings were checked.")
    return "\n".join(lines)
