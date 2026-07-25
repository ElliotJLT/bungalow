"""bungalow - turn the homebuyer-mcp into one finished home-buying pack.

The homebuyer-mcp hands an agent facts about a UK purchase: stamp duty, lease
risks, title entries, survey defects, regulated conveyancers. bungalow is the
thin layer that orchestrates those tools and presents them as a single,
prioritised due-diligence pack a buyer can act on.

The product holds no domain knowledge. Every severity, cost, and rule comes from
the MCP. bungalow orchestrates, aggregates, and renders. That is the line that
keeps the MCP the source of truth.

    from bungalow import build_report, Situation
    from bungalow.backend import MCPBackend

    report = build_report(
        Situation(postcode="SE22", price=475000, tenure="leasehold", lease_remaining_years=82),
        MCPBackend(),
    )
    print(report.headline)
"""

from __future__ import annotations

from .ask import Extraction, extract, run_ask
from .builder import Situation, SurveyIssue, build_report
from .listing import ListingFields, build_triage, situation_from_listing
from .models import DueDiligenceReport, Finding, Provider, Severity, StampDuty
from .render import render_html, render_markdown

__all__ = [
    "DueDiligenceReport",
    "Extraction",
    "Finding",
    "ListingFields",
    "Provider",
    "Severity",
    "Situation",
    "StampDuty",
    "SurveyIssue",
    "build_report",
    "build_triage",
    "extract",
    "render_html",
    "render_markdown",
    "run_ask",
    "situation_from_listing",
]

__version__ = "0.1.0"
