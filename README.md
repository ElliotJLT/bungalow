# bungalow

Turns the Clearbook MCP's home-buying tools into one finished due-diligence pack.
You give it a purchase, it comes back with a single document: stamp duty, lease
red flags, title entries, survey defects, and a prioritised list of what to do,
worst first. The kind of thing you would otherwise pay a few hundred pounds and
wait two weeks for, assembled from regulated data in one pass.

```bash
pip install -e .
bungalow demo                    # the full pack, no server or key needed
bungalow demo --html pack.html   # the same pack as a shareable web page
bungalow triage --demo           # the browse-time version (see below)
```

## The gap this fills

[Clearbook](https://github.com/ElliotJLT/homebuyer-mcp) is an MCP server. It hands
an agent facts about a UK purchase: what stamp duty is due, whether a lease has a
dangerous ground rent clause, what a survey defect means. Facts, one tool at a
time, with no opinion. That is correct for an MCP, and it is also where the buyer
is left holding six separate answers and no decision.

bungalow is the layer that turns those answers into the decision. It orchestrates
the tools, collects what they flag, and presents one prioritised pack. In the
language of an agent product: the MCP is the capability, bungalow is the finished
work.

## The design principle: no domain logic in the product

bungalow knows nothing about property. It cannot tell you what a doubling ground
rent means, what subsidence costs, or which lease length is risky. Every severity,
figure, and recommendation in the pack is the MCP's, carried through verbatim.
bungalow only orchestrates, aggregates, and renders.

This is deliberate. The MCP is the asset. A product that quietly reimplemented the
lease rules or the stamp duty bands would fork the logic, drift from the registers,
and hollow out the thing it sits on. Keeping the judgement in the MCP is what makes
bungalow strengthen it rather than replace it. There is a test that proves the line
holds: flip a flag's severity in the MCP's output and the pack follows, because the
product has no severity of its own.

## What the pack looks like

See [`sample/report.md`](sample/report.md) and
[`sample/report.html`](sample/report.html). Both are generated from real Clearbook
tool output (captured in `_sample_data.py`) for a synthetic purchase: a first-time
buyer, a leasehold flat at £475,000, with a doubling ground rent and a serious
survey finding. The pack sorts the two high-severity issues (the ground rent and
the subsidence) to the top, computes nothing itself, and ends with the actions that
actually need doing.

## Two moments: triage while browsing, the full pack once you offer

A purchase has two moments that need different packs, and both run on the same
engine and MCP.

**Browse-time triage.** You are still on the portal deciding whether a listing is
worth pursuing. The page carries price, tenure, and often the lease length and
ground rent, which is enough for the stamp duty and the lease red flags. No title,
no survey, no conveyancer search yet.

```bash
bungalow triage --price 475000 --leasehold --lease-years 82 \
                --ground-rent 250 --escalation doubling --postcode "SE22 8HR"
```

**The full pack.** Your offer is accepted and your conveyancer sends the title
register, the survey, the lease. Now `report` (or the library `build_report`) runs
the deep checks.

On sharing a URL: a listing page can be fetched, and `bungalow triage --url <link>`
will read the page title for the address and property type. But Rightmove now ships
its listing data in an obfuscated, encoded model rather than readable JSON, so price,
tenure, and lease terms are not reliably extractable from the page source. Those you
confirm. The clean way to get them automatically is a browser extension reading the
rendered page, where the values are visible regardless of the source encoding, and
posting them to the same `build_triage`. The engine already produces the pack from
partial input, so the extension is an input adapter, not a rebuild.

## How it works

```
Situation ──▶ build_report ──▶ ToolBackend ──▶ Clearbook MCP
 (what you        │                                  │
  know)           ▼                                  ▼
            DueDiligenceReport ◀── aggregate ◀── tool answers (severities, actions)
                  │
                  ▼
            Markdown / HTML pack
```

- **`Situation`** is what the buyer knows: postcode, price, tenure, and whatever
  lease, title, and survey details their conveyancer has sent so far.
- **`build_report`** decides which MCP tools to call, calls them through a
  `ToolBackend`, and assembles the findings into one report.
- **`ToolBackend`** is the seam. `MCPBackend` talks to the running Clearbook server
  over stdio. `StaticBackend` replays recorded output, which is how the demo and
  tests run with no server and no keys.
- **render** lays the report out as Markdown or a self-contained HTML page.
- An optional **brief** (`--brief`) has Claude write the two-sentence summary a
  stressed buyer reads first. Without a key it falls back to a plain summary
  composed from the findings, so the pack always leads with the headline.

## What is verified, and what needs a live setup

Honest about the boundary:

- **Tested, no key or server:** the orchestration, the aggregation and sorting, the
  "no domain logic" guarantee, both renderers, the fallback brief, and the CLI demo.
  16 tests, ruff and mypy clean.
- **Needs the live Clearbook MCP:** `MCPBackend` (the stdio client) and the
  register-backed conveyancer search, which needs the MCP's SRA and FCA API keys.
  When those are absent the pack degrades gracefully and says so.
- **Needs an Anthropic key:** the Claude brief. The fallback covers its absence.

## Limitations

- bungalow is informational, not legal or financial advice. It routes you to the
  right questions; it does not replace a conveyancer or a qualified adviser.
- It reports what the MCP returns. If a tool is wrong, the pack is wrong. The pack
  is only as good as Clearbook, which is the reason for keeping the logic there,
  where it can be fixed once.
- The pack works from what you tell it. It does not yet read a raw lease, title
  register, or survey PDF and pull out the structured facts. That extraction step (a
  natural job for Claude) is on the roadmap.

## Roadmap

- A browser extension that reads a listing's rendered page into `build_triage`,
  so the browse-time pack appears inline with zero data entry.
- Extract structured inputs from pasted lease, title, and survey documents.
- Rank conveyancers on the register facts once the SRA and FCA lookups are keyed.
- A transaction-timeline view built on the MCP's `track_transaction_status`.
- A thin web surface so a buyer never touches a terminal.

## License

MIT. See [LICENSE](LICENSE).
