# Governance OS

> **Deterministic policy engine for high-stakes finance. Gemini drafts, but never decides.**

A policy-driven coordination layer for Corporate Treasury and Wealth Management. Converts signals into policy evaluations, raises exceptions when human judgment is required, and produces audit-grade evidence packs.

**Core principle:** AI is a coprocessor, not a decision-maker. The kernel is deterministic and replayable.

### What This Actually Does

| | |
|---|---|
| **Input** | Messy evidence (PDFs, scans, emails, bank statements) |
| **Output** | Case = signals + conflicts + policy evaluation + exceptions + audit pack |
| **Guarantee** | FAIL only on confirmed breaches; observations generate review items outside the evaluator |
| **Domains** | Treasury + Wealth via "packs" (config, not forks) |

---

## Try It

```bash
# Clone and start
git clone https://github.com/Silveroboros-dev/Governance-OS.git
cd Governance-OS
docker compose up -d

# Run the demos
make demo-safety-auto    # Governance kernel blocks hallucinated breaches
make demo-thinking-auto  # Auditable extraction rationale (non-decisional)

# Run evaluations (CI gate)
make evals               # Semantic grounding verification
```

**Live endpoints:**
- UI: http://localhost:3000
- API: http://localhost:8000/docs

---

## How It Works

```
Evidence Pack → Signal Candidates → Canonicalize → Policy Evaluation → Exceptions → Human Decision → Audit Pack
  (messy docs)     (AI proposes)    (deterministic)   (deterministic)  (deterministic)   (human owns)   (archived + replayable)
```

**The AI layer (Gemini) is a coprocessor:**
- **IntakeAgent**: Extracts candidate signals with provenance (source spans)
- **NarrativeAgent**: Drafts memos grounded to evidence IDs (never invents facts)
- **PolicyDraftAgent**: Proposes policy drafts (human-approved only)

**All agent outputs are schema-validated and CI-gated with grounding + determinism checks.**

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

## Gemini as Coprocessor (LLM Never Decides Policy Outcomes)

### 1. Context Caching (Cost Reduction)

```python
from coprocessor.cache import get_cache_manager

manager = get_cache_manager()
manager.build_all_caches()  # Cache prompts + vocabularies
```

Cost reduction via context caching (workload-dependent). Caches auto-invalidate when policies change.

### 2. Rationale Summaries (Reviewable Extraction Notes)

```python
from coprocessor.agents.intake_agent import IntakeAgent

agent = IntakeAgent(use_thinking=True, thinking_budget=8192)
result = agent.extract_signals_sync(content, pack="treasury", document_source="report.pdf")

print(result.thinking_summary)
# "I identified a position limit breach because EUR/USD exposure
#  of $45.2M exceeds the stated limit of $40M..."
```

Compliance officers can review *why* each signal was extracted.

### 3. Canonicalization (Gemini Proposes, Kernel Confirms)

```bash
make evals  # Run full evaluation suite

# What it verifies:
# - Gemini extracts candidate signals from documents
# - Kernel gates unconfirmed breaches to observations (pending verification)
# - Only confirmed breaches can FAIL policy
# - Determinism: identical output across runs (hash-verified)
```

Gemini proposes breaches; the governance kernel filters hallucinations.

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

### 5. Gemini Evals (Verifier, Not Decision-Maker)

We use a Gemini-based evaluation suite as a CI verifier for coprocessor outputs.
This is NOT policy evaluation. The governance kernel remains deterministic.

```bash
make evals-gemini  # Requires GOOGLE_API_KEY
```

**What it checks:**
- **Grounding**: Every extracted claim is supported by quoted evidence spans
- **Schema compliance**: Outputs match the required structures
- **Determinism invariants**: Same input pack → same hash → same canonicalized outcome
- **Safety semantics**: Observations never cause FAIL; FAIL only on confirmed breaches

This prevents "confident but unsupported" outputs from shipping, and makes the demo replayable.

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

**Test coverage:** 500 pytest tests | **Eval coverage:** 46 eval cases (including canonicalization)

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

MCP is the firewall between AI and the governance kernel. Agents can observe and propose, but never decide. That boundary is enforced at the protocol level, not by trusting the LLM to behave. The server itself contains no AI — it's a standard tool provider, like the GitHub or Postgres MCP servers.

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
- Context Caching (cost reduction)
- Rationale Summaries (reviewable extraction notes)
- Canonicalization (Gemini proposes, kernel confirms)
- Conflict Detection
- Gemini Evals (CI verifier)

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
