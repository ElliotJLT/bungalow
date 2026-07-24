"""Browse-time triage: a pack from what a property listing shows.

Two moments in a purchase need two different packs. Once your offer is accepted
and your conveyancer sends documents, you want the full due-diligence pack (see
`build_report`). While you are still browsing, you want a fast read on whether a
listing is worth pursuing at all: the stamp duty, and any lease red flags the
listing exposes. That is triage, and it runs on the same engine and the same MCP,
just from the thinner set of facts a portal page carries.

On the URL question: a listing page can be fetched, but Rightmove now ships its
data in an obfuscated, dictionary-encoded model rather than readable JSON. The
page title is stable and gives the address and property type; price, tenure, and
lease terms are not reliably extractable server-side. So `fetch_listing_context`
is a convenience that fills in what is stable, and the buyer confirms the rest.
The reliable input is the fields, which a browser extension reading the rendered
page could supply in full.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .backend import ToolBackend
from .builder import Situation, build_report
from .models import BuyerType, DueDiligenceReport


@dataclass
class ListingFields:
    """What a listing exposes. Only price is required; the rest is filled in from
    the page or by the buyer."""

    price: int
    postcode: str = ""
    tenure: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    address: str | None = None
    lease_years: int | None = None
    ground_rent_annual: int = 0
    ground_rent_escalation: str = "unknown"
    service_charge_annual: int = 0
    source_url: str | None = None


def situation_from_listing(
    fields: ListingFields, buyer_type: BuyerType = "first_time_buyer"
) -> Situation:
    """Map listing fields to a Situation for triage.

    Providers are not searched at browse time (that belongs to the full pack once
    you are instructing a conveyancer), and title and survey are not available
    from a listing, so they are left out.
    """
    tenure = fields.tenure if fields.tenure in ("freehold", "leasehold") else "freehold"
    return Situation(
        postcode=fields.postcode,
        price=fields.price,
        buyer_type=buyer_type,
        tenure=tenure,  # type: ignore[arg-type]
        find_providers=False,
        lease_remaining_years=fields.lease_years if tenure == "leasehold" else None,
        ground_rent_annual=fields.ground_rent_annual,
        ground_rent_escalation=fields.ground_rent_escalation,
        service_charge_annual=fields.service_charge_annual,
    )


def build_triage(
    fields: ListingFields,
    backend: ToolBackend,
    buyer_type: BuyerType = "first_time_buyer",
) -> DueDiligenceReport:
    """Build a browse-time triage pack from a listing."""
    report = build_report(situation_from_listing(fields, buyer_type), backend)
    report.notes.insert(
        0,
        "Browse-time triage, based on the listing only. The full pack (title, "
        "survey, conveyancer checks) needs the documents your conveyancer sends "
        "once your offer is accepted.",
    )
    return report


_TITLE_RE = re.compile(
    r"(?P<beds>\d+)\s+bedroom\s+(?P<type>[\w \-]+?)\s+for\s+(?:sale|rent)\s+in\s+(?P<addr>.+?)\s*$",
    re.IGNORECASE,
)
_OUTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\b")


def parse_listing_title(title: str) -> ListingFields | None:
    """Pull what is stable out of a listing page title.

    Rightmove titles read like "2 bedroom flat for sale in Lordship Lane, London,
    SE22". That gives the type, bedrooms, address, and outcode reliably. Price and
    tenure are not in the title, so they are left for the buyer to confirm.
    """
    m = _TITLE_RE.search(title.strip())
    if not m:
        return None
    addr = m.group("addr").strip()
    outcode = _OUTCODE_RE.search(addr.upper())
    return ListingFields(
        price=0,
        postcode=outcode.group(1) if outcode else "",
        property_type=m.group("type").strip().lower(),
        bedrooms=int(m.group("beds")),
        address=addr,
    )


def fetch_listing_context(url: str, *, timeout: float = 20.0) -> ListingFields | None:
    """Best-effort: fetch a listing page and read its title for context.

    Returns the stable fields (type, bedrooms, address, outcode) or None if the
    page cannot be read. It deliberately does not try to decode the page's
    obfuscated data model; the buyer supplies price, tenure, and lease terms.
    """
    import urllib.request

    ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126 Safari/537.36"
    )
    request = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
            html = resp.read(200_000).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best effort, the buyer can type the fields
        return None
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    fields = parse_listing_title(match.group(1))
    if fields is not None:
        fields.source_url = url
    return fields
