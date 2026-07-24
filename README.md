# bungalow

Turns the Clearbook MCP's home-buying tools into one finished due-diligence pack.
You give it a purchase, it comes back with a single document: stamp duty, lease
red flags, title entries, survey defects, and a prioritised list of what to do,
worst first. The kind of thing you would otherwise pay a few hundred pounds and
wait two weeks for, assembled from regulated data in one pass.

```bash
pip install -e .
bungalow demo                    # prints the finished pack, no server or key needed
bungalow demo --html pack.html   # the same pack as a shareable web page
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

- Extract structured inputs from pasted lease, title, and survey documents.
- Rank conveyancers on the register facts once the SRA and FCA lookups are keyed.
- A transaction-timeline view built on the MCP's `track_transaction_status`.
- A thin web surface so a buyer never touches a terminal.

## License

MIT. See [LICENSE](LICENSE).
