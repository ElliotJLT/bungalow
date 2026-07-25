"""The bungalow command line.

    bungalow demo     render the sample pack from recorded MCP output (no server, no key)
    bungalow report   run against the live homebuyer-mcp for a real property

`demo` is the 60-second look: it produces the finished pack from real, captured
tool output so anyone can see the product work immediately.
"""

from __future__ import annotations

import argparse
import sys

from .builder import Situation, build_report
from .render import render_html, render_markdown


def _emit(report: object, args: argparse.Namespace) -> None:
    from .models import DueDiligenceReport

    assert isinstance(report, DueDiligenceReport)
    from .brief import deterministic_brief

    report.brief = deterministic_brief(report)
    if args.brief:
        from .brief import write_brief

        claude = write_brief(report)
        if claude:
            report.brief = claude
    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render_html(report))
        print(f"wrote {args.html}")
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(report))
        print(f"wrote {args.md}")
    if not args.html and not args.md:
        print(render_markdown(report))


def _cmd_demo(args: argparse.Namespace) -> int:
    from ._sample_data import SAMPLE_RESPONSES, SAMPLE_SITUATION
    from .backend import StaticBackend

    report = build_report(SAMPLE_SITUATION, StaticBackend(SAMPLE_RESPONSES))
    _emit(report, args)
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    from .backend import MCPBackend, StaticBackend
    from .listing import ListingFields, build_triage, fetch_listing_context

    if args.demo:
        from ._sample_data import SAMPLE_RESPONSES

        fields = ListingFields(
            price=475000,
            postcode="SE22 8HR",
            tenure="leasehold",
            lease_years=82,
            ground_rent_annual=250,
            ground_rent_escalation="doubling",
            service_charge_annual=1800,
        )
        backend: object = StaticBackend(SAMPLE_RESPONSES)
    else:
        if args.price is None:
            print("triage needs --price (or use --demo)", file=sys.stderr)
            return 2
        fields = ListingFields(
            price=args.price,
            postcode=args.postcode or "",
            tenure="leasehold" if args.leasehold else "freehold",
            lease_years=args.lease_years,
            ground_rent_annual=args.ground_rent,
            ground_rent_escalation=args.escalation,
            service_charge_annual=args.service_charge,
        )
        if args.url:
            context = fetch_listing_context(args.url)
            if context is not None:
                fields.address = context.address
                fields.property_type = context.property_type
                fields.bedrooms = context.bedrooms
                fields.source_url = args.url
                if not fields.postcode:
                    fields.postcode = context.postcode
            else:
                print("could not read the listing page; using the fields given", file=sys.stderr)
        backend = MCPBackend()

    from .backend import ToolBackend

    assert isinstance(backend, ToolBackend)
    report = build_triage(fields, backend, args.buyer_type)
    _emit(report, args)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from .backend import MCPBackend

    situation = Situation(
        postcode=args.postcode,
        price=args.price,
        buyer_type=args.buyer_type,
        tenure="leasehold" if args.leasehold else "freehold",
        lease_remaining_years=args.lease_years,
        ground_rent_annual=args.ground_rent,
        ground_rent_escalation=args.escalation,
        service_charge_annual=args.service_charge,
    )
    report = build_report(situation, MCPBackend())
    _emit(report, args)
    return 0


def _add_output_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--html", metavar="FILE", help="write an HTML pack to FILE")
    p.add_argument("--md", metavar="FILE", help="write a Markdown pack to FILE")
    p.add_argument(
        "--brief", action="store_true", help="add a Claude-written summary (needs a key)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bungalow", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="render the sample pack (no server or key needed)")
    _add_output_flags(demo)
    demo.set_defaults(func=_cmd_demo)

    tri = sub.add_parser(
        "triage", help="browse-time pack from a listing (stamp duty + lease flags)"
    )
    tri.add_argument("--price", type=int, default=None)
    tri.add_argument("--postcode", default="")
    tri.add_argument("--url", help="a listing URL (best-effort: reads address and type)")
    tri.add_argument(
        "--buyer-type",
        dest="buyer_type",
        choices=["first_time_buyer", "home_mover", "additional_property"],
        default="first_time_buyer",
    )
    tri.add_argument("--leasehold", action="store_true")
    tri.add_argument("--lease-years", dest="lease_years", type=int, default=None)
    tri.add_argument("--ground-rent", dest="ground_rent", type=int, default=0)
    tri.add_argument(
        "--escalation",
        choices=["none", "fixed", "rpi", "doubling", "unknown"],
        default="unknown",
    )
    tri.add_argument("--service-charge", dest="service_charge", type=int, default=0)
    tri.add_argument(
        "--demo", action="store_true", help="run on the sample listing, no server needed"
    )
    _add_output_flags(tri)
    tri.set_defaults(func=_cmd_triage)

    rep = sub.add_parser("report", help="build a pack against the live homebuyer-mcp")
    rep.add_argument("--postcode", required=True)
    rep.add_argument("--price", type=int, required=True)
    rep.add_argument(
        "--buyer-type",
        dest="buyer_type",
        choices=["first_time_buyer", "home_mover", "additional_property"],
        default="first_time_buyer",
    )
    rep.add_argument("--leasehold", action="store_true")
    rep.add_argument("--lease-years", dest="lease_years", type=int, default=None)
    rep.add_argument("--ground-rent", dest="ground_rent", type=int, default=0)
    rep.add_argument(
        "--escalation",
        choices=["none", "fixed", "rpi", "doubling", "unknown"],
        default="unknown",
    )
    rep.add_argument("--service-charge", dest="service_charge", type=int, default=0)
    _add_output_flags(rep)
    rep.set_defaults(func=_cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
