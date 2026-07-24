from __future__ import annotations

from bungalow import ListingFields, build_triage, situation_from_listing
from bungalow._sample_data import SAMPLE_RESPONSES
from bungalow.backend import StaticBackend
from bungalow.cli import main
from bungalow.listing import parse_listing_title


def _backend() -> StaticBackend:
    return StaticBackend(SAMPLE_RESPONSES)


def test_situation_from_listing_skips_providers_and_docs() -> None:
    fields = ListingFields(price=475000, postcode="SE22", tenure="leasehold", lease_years=82)
    situation = situation_from_listing(fields)
    assert situation.find_providers is False  # no conveyancer search at browse time
    assert situation.title_provided is False
    assert situation.survey_issues == []
    assert situation.lease_remaining_years == 82


def test_freehold_listing_has_no_lease_years() -> None:
    situation = situation_from_listing(ListingFields(price=300000, tenure="freehold"))
    assert situation.lease_remaining_years is None


def test_triage_pack_has_stamp_duty_and_lease_flags_only() -> None:
    fields = ListingFields(
        price=475000,
        postcode="SE22 8HR",
        tenure="leasehold",
        lease_years=82,
        ground_rent_annual=250,
        ground_rent_escalation="doubling",
        service_charge_annual=1800,
    )
    report = build_triage(fields, _backend())
    assert report.stamp_duty is not None
    sources = {f.source for f in report.findings}
    assert sources == {"lease"}  # no title or survey at browse time
    assert any("triage" in n.lower() for n in report.notes)


def test_parse_listing_title_pulls_stable_fields() -> None:
    fields = parse_listing_title("2 bedroom flat for sale in Lordship Lane, London, SE22")
    assert fields is not None
    assert fields.bedrooms == 2
    assert fields.property_type == "flat"
    assert fields.postcode == "SE22"
    assert fields.price == 0  # not in the title, buyer confirms


def test_parse_listing_title_returns_none_on_junk() -> None:
    assert parse_listing_title("Rightmove homepage") is None


def test_cli_triage_demo(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["triage", "--demo"]) == 0
    out = capsys.readouterr().out
    assert "Doubling ground rent" in out
    assert "triage" in out.lower()
