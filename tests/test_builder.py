from __future__ import annotations

import pytest

from bungalow import Severity, build_report
from bungalow._sample_data import SAMPLE_RESPONSES, SAMPLE_SITUATION
from bungalow.backend import StaticBackend
from bungalow.builder import Situation


def _report():
    return build_report(SAMPLE_SITUATION, StaticBackend(SAMPLE_RESPONSES))


def test_report_aggregates_all_sources() -> None:
    report = _report()
    sources = {f.source for f in report.findings}
    assert sources == {"lease", "title", "survey"}


def test_stamp_duty_carried_from_mcp() -> None:
    report = _report()
    assert report.stamp_duty is not None
    assert report.stamp_duty.total == 8750  # the MCP's number, verbatim


def test_doubling_ground_rent_is_high_and_sorts_first() -> None:
    report = _report()
    top = report.sorted_findings()[0]
    assert top.severity is Severity.HIGH
    assert "ground rent" in top.issue.lower()


def test_overall_severity_is_high() -> None:
    assert _report().overall_severity is Severity.HIGH


def test_survey_finding_is_high_from_urgency() -> None:
    report = _report()
    survey = [f for f in report.findings if f.source == "survey"]
    assert len(survey) == 1
    assert survey[0].severity is Severity.HIGH


def test_empty_provider_search_adds_a_note() -> None:
    report = _report()
    assert report.providers == []
    assert any("register lookup" in n.lower() for n in report.notes)


def test_product_holds_no_severity_of_its_own() -> None:
    # Every finding's severity must be one the MCP supplied. If we flip the MCP's
    # HIGH to LOW, the report follows, proving the product does not re-judge.
    tampered = {**SAMPLE_RESPONSES}
    lease = {**tampered["check_lease_terms"]}
    lease["flags"] = [{**f, "severity": "LOW"} for f in lease["flags"]]
    tampered["check_lease_terms"] = lease
    report = build_report(SAMPLE_SITUATION, StaticBackend(tampered))
    lease_findings = [f for f in report.findings if f.source == "lease"]
    assert all(f.severity is Severity.LOW for f in lease_findings)


def test_freehold_skips_lease_call() -> None:
    situation = Situation(postcode="N1 1AA", price=300000, tenure="freehold", find_providers=False)
    responses = {"estimate_stamp_duty": SAMPLE_RESPONSES["estimate_stamp_duty"]}
    report = build_report(situation, StaticBackend(responses))  # would KeyError if it called lease
    assert report.findings == []


def test_static_backend_raises_on_missing_tool() -> None:
    with pytest.raises(KeyError):
        StaticBackend({}).call("estimate_stamp_duty", {})
