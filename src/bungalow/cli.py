"""The bungalow command line.

    bungalow demo     render the sample pack from recorded MCP output (no server, no key)
    bungalow report   run against the live Clearbook MCP for a real property

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

    rep = sub.add_parser("report", help="build a pack against the live Clearbook MCP")
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
