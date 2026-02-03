# Governance OS

> **Deterministic policy engine for high-stakes finance. Gemini drafts, but never decides. Zero hallucinations verified.**

A policy-driven coordination layer for Corporate Treasury and Wealth Management. Converts signals into policy evaluations, raises exceptions when human judgment is required, and produces audit-grade evidence packs.

**Core principle:** AI is a coprocessor, not a decision-maker. The kernel is deterministic and replayable.

---

## Gemini 3 Features

| Feature | What It Does | Benefit |
|---------|--------------|---------|
| **Context Caching** | Caches agent prompts + vocabularies | 50-60% cost reduction at scale |
| **Thinking Mode** | Exposes reasoning chain for extractions | Audit-grade AI transparency |
| **Semantic Eval Judge** | Gemini validates grounding to evidence | Zero hallucinations (CI-verified) |
| **Native JSON + Conflicts** | Detects when sources disagree | Surfaces contradictions for review |

---

## Try It

```bash
# Clone and start
git clone https://github.com/Silveroboros-dev/Governance-OS.git
cd Governance-OS
docker compose up -d

# Run the demos
make demo-safety-auto    # Watch AI hallucinations get BLOCKED
make demo-thinking-auto  # See Gemini's reasoning chain exposed

# Run evaluations (CI gate)
make evals               # Zero tolerance for unsupported claims
```

**Live endpoints:**
- UI: http://localhost:3000
- API: http://localhost:8000/docs

---

## How It Works

```
Signal → Policy Evaluation → Exception → Human Decision → Evidence Pack
           (deterministic)     (AI drafts)    (human owns)    (audit-grade)
```

**The AI layer (Gemini 3):**
- **IntakeAgent**: Extracts signals from documents with source spans + confidence scores
- **NarrativeAgent**: Drafts memos grounded to evidence IDs (never invents facts)
- **PolicyDraftAgent**: Generates policy drafts from natural language (human-approved only)

**All agent outputs are schema-validated and eval-gated. CI fails on any hallucination.**

---

## Gemini 3 Integration Details

### 1. Context Caching (50-60% Cost Reduction)

```python
from coprocessor.cache import get_cache_manager

manager = get_cache_manager()
manager.build_all_caches()  # Cache prompts + vocabularies

# Cached tokens cost 90% less; overall savings 50-60% per request
```

Caches auto-invalidate when policies change. No stale context.

### 2. Thinking Mode (Audit-Grade Transparency)

```python
from coprocessor.agents.intake_agent import IntakeAgent

agent = IntakeAgent(use_thinking=True, thinking_level="high")
result = agent.extract_signals_sync(content, pack="treasury", document_source="report.pdf")

print(result.thinking_summary)
# "I identified a position limit breach because EUR/USD exposure
#  of $45.2M exceeds the stated limit of $40M..."
```

Compliance officers can review *why* each signal was extracted.

### 3. Semantic Eval Judge (Zero Hallucinations)

```bash
make evals-gemini  # Gemini validates narrative grounding

# Catches what regex can't:
# - Wrong numbers ("$50M" when evidence says "$45M")
# - Unsupported causal claims
# - Fabricated evidence references
```

Two-stage pipeline: fast regex first, then Gemini semantic verification.

### 4. Conflict Detection (When Sources Disagree)

```python
# ExtractionResult now includes:
result.conflicts  # List of source disagreements
result.drops      # What couldn't be extracted (with reason)

# Example conflict:
# C1: Cash Position
#   - weekly-pack.pdf: "$85,240" (internal_reported)
#   - bank-statement.pdf: "$62,184" (ledger)
#   - Flags: [VALUE_DATE_MISMATCH, BLOCKER]
```

Contradictions are surfaced, not silently resolved.

---

## AI Safety Boundaries (Non-Negotiable)

| Allowed | Not Allowed |
|---------|-------------|
| Extract candidate signals (with provenance) | Policy evaluation |
| Draft memos (grounded to evidence) | Severity/escalation decisions |
| Generate policy drafts (human-approved) | "Recommended option" in UI |
| Surface conflicts between sources | Silent writes without audit |

**The kernel is deterministic. LLMs are optional coprocessors.**

---

## Architecture

```
/core         FastAPI backend (deterministic governance kernel)
/ui           Next.js frontend (one-screen decision UI)
/coprocessor  Gemini-powered agents + prompts + schemas
/evals        Datasets + goldens + CI-gated eval runner
/mcp_server   MCP server for AI agent integration
/packs        Domain packs (treasury, wealth)
```

**Test coverage:** 302 tests | **Eval coverage:** 28 golden test cases

---

## Quick Commands

```bash
make up              # Start all services
make demo-safety     # AI safety demo (interactive)
make demo-thinking   # Thinking mode demo (interactive)
make evals           # Run full eval suite
make evals-gemini    # Run Gemini semantic verification
```

---

<details>
<summary><strong>Full Documentation</strong> (click to expand)</summary>

## Why This Exists

Modern exec workflows are continuous, but decision-making is episodic (meetings, decks, month-end rituals). That creates:
- Late detection of risk/regime shifts
- False certainty from dashboards
- Brittle automation without accountability
- Loss of institutional memory

Governance OS is a **control-plane**: autonomous where safe, interruption-driven where judgment is required.

## Key Concepts

- **Policy / PolicyVersion**: Explicit, versioned rules with change control
- **Signal**: Timestamped facts with provenance (source, reliability)
- **Evaluation**: Deterministic result of applying policy to signals
- **Exception**: Interruption when judgment is required (deduped, severity-tagged)
- **Decision**: Immutable commitment with rationale + assumptions
- **AuditEvent**: Append-only trail of meaningful state changes
- **Evidence Pack**: Deterministic bundle answering "why did we do this?"

## Domain Packs

Treasury and Wealth are implemented as **packs** (configuration), not forks.

### Treasury Pack

**Signal Types (8):**
- `position_limit_breach` - Asset position exceeds limit
- `market_volatility_spike` - Volatility exceeds threshold
- `counterparty_credit_downgrade` - Credit rating downgraded
- `liquidity_threshold_breach` - Liquidity below required level
- `fx_exposure_breach` - FX exposure exceeds limit
- `cash_forecast_variance` - Cash position deviates from forecast
- `covenant_breach` - Financial covenant violated
- `settlement_failure` - Trade settlement failed

### Wealth Pack

**Signal Types (8):**
- `portfolio_drift` - Allocation drifted from target
- `rebalancing_required` - Rebalancing threshold triggered
- `suitability_mismatch` - Client risk profile vs holdings
- `concentration_breach` - Single position concentration
- `tax_loss_harvest_opportunity` - Tax-loss harvesting signal
- `client_cash_withdrawal` - Large withdrawal request
- `market_correlation_spike` - Portfolio correlation risk
- `fee_schedule_change` - Fee changes affecting client

## MCP Server (AI Agent Integration)

The MCP server exposes the governance kernel to AI agents via Model Context Protocol.

**Read Tools:**
- `get_open_exceptions` - List exceptions requiring decisions
- `get_exception_detail` - Full context for an exception
- `get_policies` - List active policies
- `get_evidence_pack` - Complete evidence for a decision

**Write Tools (all require human approval):**
- `propose_signal` - Propose candidate signal → approval queue
- `propose_policy_draft` - Propose policy draft → approval queue
- `dismiss_exception` - Propose dismissal → approval queue

### Claude Desktop Integration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "governance-os": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Governance-OS",
      "env": {
        "DATABASE_URL": "postgresql://govos:local_dev_password@localhost:5432/governance_os"
      }
    }
  }
}
```

## Replay Harness (Policy Tuning)

```bash
make replay PACK=treasury FROM=2025-01-01 TO=2025-03-31
```

- Import historical signals (CSV)
- Evaluate against current policy set
- Generate exceptions deterministically
- Tune thresholds and compare before/after

## Implementation Status

### Sprint 1: Kernel (Complete)
- Deterministic governance kernel
- Immutable decision recording
- Evidence packs
- One-screen decision UI
- Treasury pack

### Sprint 2: Packs + Replay + AI (Complete)
- Wealth Pack
- Replay Harness
- MCP Server (read-only)
- NarrativeAgent v0
- Evals v0

### Sprint 3: Agentic Coprocessor (Complete)
- MCP Write Tools with approval gates
- IntakeAgent (document → signals)
- PolicyDraftAgent
- Agent Tracing
- Expanded Evals

### Gemini 3 Hackathon (Current)
- Context Caching (50-60% savings)
- Thinking Mode (audit transparency)
- Semantic Eval Judge
- Conflict Detection

## Contributing

Contributions welcome:
- Policy schemas and evaluators
- Replay harness features
- UI improvements
- Connectors (read-only first)

Please open an issue first for non-trivial changes.

## License

MIT (see LICENSE).

## Disclaimer

Governance OS is decision-support tooling. It does not provide financial, investment, tax, or legal advice.

</details>
