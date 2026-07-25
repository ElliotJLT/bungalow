"""Recorded outputs from a real homebuyer-mcp session.

These are genuine tool responses captured from the live MCP, not invented. They
drive `bungalow demo` and the tests so the product can be exercised end to end
with no server and no API keys. The scenario is a synthetic but realistic
purchase: a first-time buyer, a leasehold flat in SE22 at £475,000, with a
doubling ground rent, a short-ish lease, standard title entries, and a serious
survey finding.
"""

from __future__ import annotations

from typing import Any

from .builder import Situation, SurveyIssue

SAMPLE_SITUATION = Situation(
    postcode="SE22 8HR",
    price=475000,
    buyer_type="first_time_buyer",
    tenure="leasehold",
    find_providers=True,
    lease_remaining_years=82,
    ground_rent_annual=250,
    ground_rent_escalation="doubling",
    service_charge_annual=1800,
    has_sinking_fund=False,
    lease_type="flat",
    title_provided=True,
    title_class="absolute",
    has_restrictive_covenants=True,
    has_charges=True,
    charge_types="mortgage",
    restrictions="mortgage_restriction",
    survey_issues=[SurveyIssue(issue_type="subsidence", condition_rating=3)],
)

SAMPLE_RESPONSES: dict[str, dict[str, Any]] = {
    "estimate_stamp_duty": {
        "purchase_price": 475000,
        "buyer_type": "first-time buyer",
        "additional_property": False,
        "base_tax": 8750,
        "additional_property_surcharge": 0,
        "total_stamp_duty": 8750,
        "effective_rate_percent": 1.84,
        "country": "England & Northern Ireland",
        "note": (
            "SDLT rates from 1 April 2025. Temporary higher nil-rate bands "
            "(Sep 2022-Mar 2025) have reverted."
        ),
    },
    "search_conveyancers": {"providers": [], "total_count": 0, "data_sources": []},
    "check_lease_terms": {
        "overall_assessment": "CONCERNING - address high-severity issues before proceeding",
        "remaining_years": 82,
        "flags": [
            {
                "issue": "Lease approaching critical threshold",
                "severity": "MEDIUM",
                "detail": (
                    "At 82 years, the lease is getting short. While still mortgageable, "
                    "you should plan to extend within 2 years of purchase (you gain the "
                    "statutory right after 2 years). Extending before it drops below 80 "
                    "saves significant cost."
                ),
                "action": (
                    "Budget for a lease extension. Get a valuation now to understand the cost."
                ),
            },
            {
                "issue": "Doubling ground rent clause",
                "severity": "HIGH",
                "detail": (
                    "Ground rent of £250/year with a doubling clause is a serious red "
                    "flag. This was the pattern that led to the leasehold scandal. Some "
                    "lenders (including Nationwide and Santander) refuse to lend on "
                    "properties with doubling ground rent clauses."
                ),
                "action": (
                    "Check if the freeholder will agree to vary the clause to RPI-linked "
                    "or fixed. If not, consider whether you can get a mortgage - check "
                    "with your lender first. This may significantly affect resale value."
                ),
            },
            {
                "issue": "Ground rent at or above £250/year",
                "severity": "MEDIUM",
                "detail": (
                    "Ground rent of £250/year is above the £250 threshold. If ground "
                    "rent reaches £250+ (or £1,000+ in London), the lease could "
                    "technically be treated as an Assured Shorthold Tenancy under the "
                    "Housing Act 1988, giving the freeholder potential forfeiture rights."
                ),
                "action": (
                    "Ask your solicitor to advise on AST risk. The Leasehold Reform "
                    "(Ground Rent) Act 2022 caps new leases at peppercorn but doesn't "
                    "apply to existing leases."
                ),
            },
            {
                "issue": "No reserve/sinking fund",
                "severity": "MEDIUM",
                "detail": (
                    "The building has no reserve fund for major works. This means when "
                    "significant repairs are needed (roof, windows, external decoration), "
                    "leaseholders will face a large one-off bill, potentially "
                    "£5,000-£20,000+."
                ),
                "action": (
                    "Ask to see any planned major works. Ask the management company about "
                    "the building's condition and when major works are expected."
                ),
            },
        ],
        "flag_count": {"high": 1, "medium": 3, "low": 0},
    },
    "parse_title_register": {
        "overall_assessment": "STANDARD - minor items, nothing unusual",
        "title_class": "absolute",
        "tenure": "leasehold",
        "proprietor_count": 1,
        "flags": [
            {
                "section": "C - Charges",
                "issue": "Mortgage",
                "severity": "LOW",
                "detail": (
                    "Standard mortgage charge. Will be paid off from sale proceeds on completion."
                ),
                "action": "No action needed - your solicitor handles mortgage redemption.",
            },
            {
                "section": "B - Proprietorship",
                "issue": "Mortgage Restriction",
                "severity": "LOW",
                "detail": (
                    "Standard restriction placed by the mortgage lender. This will be "
                    "removed when the seller pays off their mortgage on completion."
                ),
                "action": (
                    "No action needed - your solicitor will ensure this is removed on completion."
                ),
            },
            {
                "section": "A - Property",
                "issue": "Restrictive covenants",
                "severity": "LOW",
                "detail": (
                    "The property is subject to restrictive covenants - rules about what "
                    "you can and can't do with the property. Many are historic and rarely "
                    "enforced, but technically still binding."
                ),
                "action": (
                    "Review the specific covenants with your solicitor. Indemnity "
                    "insurance is available for breaches of historic covenants."
                ),
            },
        ],
        "flag_count": {"high": 0, "medium": 0, "low": 3},
    },
    "explain_survey_issue": {
        "issue_type": "subsidence",
        "condition_rating": 3,
        "condition_label": "Serious defects - urgent repairs needed",
        "plain_english": (
            "The building's foundations are sinking unevenly, causing the structure to "
            "move. This is different from 'settlement' (which is normal and usually stops)."
        ),
        "estimated_cost": "£5,000-£50,000+",
        "urgency": "HIGH",
        "specialist_needed": "Structural engineer",
        "insurance_impact": (
            "May trigger excess of £1,000+ on subsidence claims. Previous subsidence "
            "claims must be disclosed to insurers."
        ),
        "recommendation": (
            "This is rated Condition 3 (urgent). Get a structural engineer report before "
            "exchange. Consider negotiating a price reduction or making repair a condition "
            "of purchase."
        ),
    },
}
