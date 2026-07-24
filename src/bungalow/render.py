"""Render a report as Markdown or as a self-contained HTML page.

The HTML is the visible artifact: one page a buyer can read top to bottom and
act on. Nothing here computes or judges; it lays out what the builder collected.
"""

from __future__ import annotations

from .models import DueDiligenceReport, Finding, Severity

_SEV_LABEL = {Severity.HIGH: "HIGH", Severity.MEDIUM: "MEDIUM", Severity.LOW: "LOW"}
_SEV_COLOUR = {Severity.HIGH: "#c0362c", Severity.MEDIUM: "#b8860b", Severity.LOW: "#4a7a4a"}


def _money(n: int) -> str:
    return f"£{n:,}"


def render_markdown(report: DueDiligenceReport) -> str:
    lines: list[str] = []
    tenure = report.tenure
    lines.append("# bungalow due-diligence pack")
    lines.append("")
    lines.append(
        f"**{report.postcode}** · {_money(report.price)} · {tenure} · "
        f"{report.buyer_type.replace('_', ' ')}"
    )
    lines.append(f"_Generated {report.generated_at:%Y-%m-%d %H:%M} UTC_")
    lines.append("")
    lines.append(f"## {report.headline}")
    lines.append("")
    if report.brief:
        lines.append(report.brief)
        lines.append("")

    if report.stamp_duty:
        sd = report.stamp_duty
        lines.append("## Money")
        lines.append("")
        lines.append(
            f"Stamp duty: **{_money(sd.total)}** ({sd.effective_rate}% effective, "
            f"{sd.buyer_type})."
        )
        if sd.note:
            lines.append(f"> {sd.note}")
        if sd.caveat:
            lines.append(f"> Check: {sd.caveat}")
        lines.append("")

    findings = report.sorted_findings()
    if findings:
        lines.append("## Red flags, worst first")
        lines.append("")
        for f in findings:
            lines.append(f"### [{_SEV_LABEL[f.severity]}] {f.issue}  ({f.source})")
            lines.append("")
            lines.append(f.detail)
            if f.action:
                lines.append("")
                lines.append(f"**Do:** {f.action}")
            lines.append("")

    lines.append("## Your conveyancer")
    lines.append("")
    if report.providers:
        for p in report.providers:
            trailing = f" (trading since {p.detail})" if p.detail else ""
            lines.append(f"- **{p.name}** - {p.status}{trailing}")
    else:
        lines.append("_No firms returned. See notes._")
    lines.append("")

    actions = _actions(findings)
    if actions:
        lines.append("## Next actions")
        lines.append("")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_bungalow assembles facts from the Clearbook MCP into one document. It is "
        "informational, not legal or financial advice, and does not replace your "
        "conveyancer or a qualified adviser. Confirm anything that matters with them._"
    )
    return "\n".join(lines)


def _actions(findings: list[Finding]) -> list[str]:
    # Next actions are the things that actually need doing. LOW findings are
    # routine ("no action needed, your solicitor handles it"), so they are shown
    # in the flags list but not repeated here.
    seen: set[str] = set()
    out: list[str] = []
    for f in findings:
        if f.severity is Severity.LOW:
            continue
        if f.action and f.action not in seen:
            seen.add(f.action)
            out.append(f.action)
    return out


def render_html(report: DueDiligenceReport) -> str:
    from html import escape

    parts: list[str] = []
    parts.append(
        f"<p class='meta'>{escape(report.postcode)} &middot; {_money(report.price)} "
        f"&middot; {escape(report.tenure)} &middot; "
        f"{escape(report.buyer_type.replace('_', ' '))}</p>"
    )
    parts.append(f"<h1>{escape(report.headline)}</h1>")
    if report.brief:
        parts.append(f"<p class='brief'>{escape(report.brief)}</p>")

    if report.stamp_duty:
        sd = report.stamp_duty
        parts.append("<h2>Money</h2>")
        parts.append(
            f"<p>Stamp duty: <strong>{_money(sd.total)}</strong> "
            f"({escape(str(sd.effective_rate))}% effective, {escape(sd.buyer_type)}).</p>"
        )
        if sd.note:
            parts.append(f"<p class='note'>{escape(sd.note)}</p>")

    findings = report.sorted_findings()
    if findings:
        parts.append("<h2>Red flags, worst first</h2>")
        for f in findings:
            colour = _SEV_COLOUR[f.severity]
            parts.append("<div class='finding'>")
            parts.append(
                f"<span class='sev' style='background:{colour}'>"
                f"{_SEV_LABEL[f.severity]}</span> "
                f"<strong>{escape(f.issue)}</strong> "
                f"<span class='src'>{escape(f.source)}</span>"
            )
            parts.append(f"<p>{escape(f.detail)}</p>")
            if f.action:
                parts.append(f"<p class='do'><strong>Do:</strong> {escape(f.action)}</p>")
            parts.append("</div>")

    parts.append("<h2>Your conveyancer</h2>")
    if report.providers:
        parts.append("<ul>")
        for p in report.providers:
            trailing = f" (trading since {escape(p.detail)})" if p.detail else ""
            parts.append(
                f"<li><strong>{escape(p.name)}</strong> - {escape(p.status)}{trailing}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p class='note'>No firms returned. See notes.</p>")

    actions = _actions(findings)
    if actions:
        parts.append("<h2>Next actions</h2><ul>")
        for a in actions:
            parts.append(f"<li>{escape(a)}</li>")
        parts.append("</ul>")

    if report.notes:
        parts.append("<h2>Notes</h2><ul>")
        for n in report.notes:
            parts.append(f"<li>{escape(n)}</li>")
        parts.append("</ul>")

    body = "\n".join(parts)
    return _HTML_SHELL.format(body=body)


_HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bungalow due-diligence pack</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; line-height: 1.55;
         max-width: 720px; margin: 2.5rem auto; padding: 0 1.2rem; color: #1b1b1b; }}
  h1 {{ font-size: 1.6rem; margin: .2rem 0 1rem; }}
  h2 {{ font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid #eee;
        padding-bottom: .3rem; }}
  .meta {{ color: #666; font-size: .9rem; margin: 0; }}
  .brief {{ background: #f6f5f1; padding: 1rem 1.2rem; border-radius: 8px; }}
  .finding {{ margin: 1rem 0; padding-left: .2rem; }}
  .sev {{ color: #fff; font-size: .72rem; font-weight: 700; padding: .1rem .45rem;
          border-radius: 4px; letter-spacing: .03em; }}
  .src {{ color: #888; font-size: .8rem; }}
  .do {{ color: #222; }}
  .note {{ color: #666; font-size: .9rem; }}
  footer {{ margin-top: 2.5rem; color: #888; font-size: .82rem; border-top: 1px solid #eee;
            padding-top: 1rem; }}
</style>
</head>
<body>
{body}
<footer>bungalow assembles facts from the Clearbook MCP into one document. It is
informational, not legal or financial advice, and does not replace your conveyancer
or a qualified adviser. Confirm anything that matters with them.</footer>
</body>
</html>
"""
