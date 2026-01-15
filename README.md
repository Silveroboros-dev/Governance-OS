# Governance OS

> **Governance OS is a policy-driven exception/decision engine with a deterministic core and an integrated, evaluated agent layer.**

Governance OS is a policy-driven coordination layer for high-stakes professional work (starting with **Corporate Treasury** and **Wealth Management**).

It converts continuous signals into deterministic policy evaluations, raises exceptions only when **human judgment** is required, captures accountable decisions (with rationale and assumptions), and produces audit-grade evidence packs. The core is **replayable** on historical data to tune precision and reduce coordination overhead.

**Core loop:** Signal → Policy Evaluation → Exception → Decision → Evidence/Outcome

---

## Why this exists

Modern exec workflows are continuous, but decision-making is episodic (meetings, decks, month-end rituals). That creates:
- late detection of risk/regime shifts  
- false certainty from dashboards  
- brittle automation without accountability  
- loss of institutional memory  

Governance OS is built as a **control-plane**: autonomous where safe, interruption-driven where judgment is required.

---

## Code-first proof points

| Artifact | Path |
|----------|------|
| Eval runner (CI-gated) | [`evals/runner.py`](evals/runner.py) |
| Agent prompts (versioned) | [`coprocessor/prompts/`](coprocessor/prompts/) |
| Core determinism tests | [`core/tests/test_determinism.py`](core/tests/test_determinism.py) |
| Structured logging | [`core/logging.py`](core/logging.py) |
| Runbook | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) |

**Planned:**
- MCP tool contracts: `mcp/schemas/*.json`
- Trace viewer: `coprocessor/traces/`
- Demo scripts: `make demo-treasury`, `make demo-wealth`

---

## AI Engineering Proof (verifiable, not vibes)

This repo is designed to demonstrate **responsible agentic engineering**: tool contracts, schema discipline, eval gates, and traces.

### 1) Deterministic governance kernel (shipped first)
- Replayable policy evaluation (same inputs → same outputs)
- Exception → decision → audit trail
- Deterministic evidence packs (“why did we do this?”)

### 2) Agentic coprocessor (LLM layer; gated, traced, eval-tested)
- Agents operate only through **tool contracts** (MCP)
- Agent outputs are **schema-validated**
- Narrative outputs must be **grounded to evidence IDs** (eval-gated)

### 3) Evals (fail CI on hallucinations)
- Narrative faithfulness: zero unsupported claims
- Kernel regression: replay determinism



### ✅ Implemented (Sprint 1)
- Deterministic governance kernel (policy → evaluation → exception → decision)
- Immutable decision recording with rationale and assumptions
- Evidence packs for defensibility and audit
- One-screen decision UI (no recommendations, symmetric options)
- Treasury pack with realistic policies, signals, and demo scenarios

### ✅ Implemented (Sprint 2)
- **Wealth Pack**: 8 signal types, 8 policies, 7 demo scenarios
- **Replay Harness**: CSV ingestion with provenance, deterministic replay, comparison tools
- **MCP Server (read-only tools)**: Exposes kernel state safely for AI agents
- **NarrativeAgent v0**: Drafts memos strictly grounded to evidence IDs
- **Evals v0**: CI fails on unsupported claims (anti-hallucination gate)
- **Exception Metrics**: Budget tracking and replay analytics

### ✅ Implemented (Sprint 3)
- **MCP Write Tools**: Gated write operations (propose_signal, propose_policy_draft, dismiss_exception) with approval queue
- **IntakeAgent**: Extract candidate signals from unstructured documents with provenance, confidence scores, and source spans
- **PolicyDraftAgent**: Generate policy drafts from natural language descriptions with test scenarios
- **Approval Queue**: Human-in-the-loop gating for all agent-proposed writes
- **Agent Tracing**: Full observability for agent executions (tool calls, timing, errors)
- **Trace Viewer UI**: Browse agent runs, inspect tool calls, approve/reject proposals
- **Expanded Evals**: Extraction accuracy (precision/recall/F1), kernel regression, policy draft validation
- **CI Eval Gate**: GitHub Actions workflow fails on eval regressions

## AI safety boundaries (non-negotiable)

The kernel is deterministic. LLMs are optional coprocessors and never the source of truth for policy evaluation, escalation, or evidence.

Allowed:
- unstructured → candidate signals (with provenance + confidence + source spans)
- memo drafts grounded to evidence IDs
- policy draft generation (never auto-publish)

Not allowed:
- policy evaluation
- severity/escalation decisions
- “recommended option” in the commitment UI
- silent writes without approvals/audit events


---

## What this is (and is not)

### This is
- A **governance kernel**: policies, evaluations, exceptions, decisions, audit trail
- A **one-screen decision surface** (no chat, no “AI recommends”)
- A **system of record for judgment** with deterministic evidence packs
- A **replay harness** for tuning policies without production risk

### This is not
- A BI dashboard
- A copilot/chat-first experience
- RPA that executes without explicit boundaries
- A model showcase

---

## Key concepts

- **Policy / PolicyVersion**: explicit, versioned rules with change control
- **Signal**: timestamped facts with provenance (source, reliability)
- **Evaluation**: deterministic result of applying policy to signals
- **Exception**: interruption when judgment is required (deduped, severity-tagged)
- **Decision**: immutable commitment with rationale + assumptions
- **AuditEvent**: append-only trail of meaningful state changes
- **Evidence Pack**: deterministic bundle answering “why did we do this?”

---

## Repo layout
```bash
  /core        FastAPI backend (deterministic governance kernel)
  /ui          Next.js frontend (one-screen exception UI + supporting views)
  /db          Migrations, schema, seed hooks
  /packs       Domain packs (treasury, wealth): templates + fixtures + vocabulary
  /replay      Replay harness: CSV import + scenario runner + metrics
  /tests       Comprehensive test suite (302 tests)

  # AI engineering layer
  /mcp_server  MCP server exposing kernel tools (read-only + gated writes via approval queue)
  /coprocessor Agents + tools + prompts + schemas + traces
  /evals       Datasets + goldens + eval runner (CI-gated)
```

### Domain packs (Treasury + Wealth)
Treasury and Wealth are implemented as **packs** (configuration), not forks:
- signal types
- policy templates
- option templates
- UI copy / vocabulary
- fixtures for demos and replay

#### Treasury Pack (included)

**Signal Types (8):**
- `position_limit_breach` - Asset position exceeds limit
- `market_volatility_spike` - Volatility exceeds threshold
- `counterparty_credit_downgrade` - Credit rating downgraded
- `liquidity_threshold_breach` - Liquidity below required level
- `fx_exposure_breach` - FX exposure exceeds limit
- `cash_forecast_variance` - Cash position deviates from forecast
- `covenant_breach` - Financial covenant violated
- `settlement_failure` - Trade settlement failed

**Policies (8):**
- Position Limit Policy
- Market Volatility Policy
- Counterparty Credit Risk Policy
- Liquidity Management Policy
- FX Exposure Policy
- Cash Forecasting Policy
- Covenant Monitoring Policy
- Settlement Risk Policy

**Demo Scenarios (7):** Realistic treasury scenarios in `packs/treasury/fixtures/scenarios.json`

```bash
# Load realistic demo scenarios
docker compose exec backend python -m core.scripts.seed_fixtures --scenarios

# Load specific scenario
docker compose exec backend python -m core.scripts.seed_fixtures --scenario=btc_position_breach_critical
```

#### Wealth Pack (Sprint 2)

**Signal Types (8):**
- `portfolio_drift` - Allocation drifted from target
- `rebalancing_required` - Rebalancing threshold triggered
- `suitability_mismatch` - Client risk profile vs holdings
- `concentration_breach` - Single position concentration
- `tax_loss_harvest_opportunity` - Tax-loss harvesting signal
- `client_cash_withdrawal` - Large withdrawal request
- `market_correlation_spike` - Portfolio correlation risk
- `fee_schedule_change` - Fee changes affecting client

**Policies (8):**
- Portfolio Drift Policy
- Rebalancing Policy
- Suitability Policy
- Concentration Policy
- Tax Loss Harvesting Policy
- Withdrawal Policy
- Correlation Risk Policy
- Fee Change Policy

**Demo Scenarios (7):** Realistic wealth management scenarios in `packs/wealth/fixtures/scenarios.json`

---

## Quick start (local)

### Prerequisites
- Docker + Docker Compose (required)
- Python 3.11+ (optional, for local development)

### Run the system

```bash
# Start all services (postgres + backend + frontend)
docker compose up -d

# View logs
docker compose logs -f
```

The system will automatically:
- Start PostgreSQL database
- Run Alembic migrations
- Seed treasury fixtures (policies)
- Start the FastAPI backend
- Start the Next.js frontend

### Access the application

- **Frontend UI:** http://localhost:3000
- **API Documentation:** http://localhost:8000/docs
- **API Base URL:** http://localhost:8000/api/v1
- **Health Check:** http://localhost:8000/health

### Frontend pages

- `/exceptions` - View open exceptions requiring decisions
- `/exceptions/[id]` - One-screen decision UI (no recommendations)
- `/decisions` - Decision history with audit trail
- `/decisions/[id]` - Evidence viewer with export
- `/policies` - Policy list (read-only)

### Common commands

```bash
make up           # Start all services
make down         # Stop all services
make logs         # View logs
make shell        # Open backend shell
make db           # Open postgres shell
make clean        # Remove all containers and volumes
```

### Sprint 2 commands

```bash
# Replay harness (policy tuning)
make replay PACK=treasury FROM=2025-01-01 TO=2025-03-31

# MCP server (for Claude Desktop integration)
make mcp

# Run evaluations (CI gate - fails on hallucinations)
make evals

# Load demo scenarios
make scenarios
```

### MCP Server (AI Agent Integration)

The MCP server exposes the governance kernel to AI agents via Model Context Protocol.

#### Available Tools

**Read Tools:**
- `get_open_exceptions` - List exceptions requiring decisions
- `get_exception_detail` - Full context for an exception
- `get_policies` - List active policies
- `get_policy_detail` - Full policy with rule definition
- `get_evidence_pack` - Complete evidence for a decision
- `search_decisions` - Search decision history
- `get_recent_signals` - Recent signals

**Write Tools (Sprint 3 - all require human approval):**
- `propose_signal` - Propose candidate signal → approval queue
- `propose_policy_draft` - Propose policy draft → approval queue
- `dismiss_exception` - Propose dismissal → approval queue
- `add_exception_context` - Enrich exception (no approval needed)

#### Testing with MCP Inspector

```bash
# Start MCP Inspector (requires postgres running)
docker compose up -d postgres

DATABASE_URL="postgresql://govos:local_dev_password@localhost:5432/governance_os" \
  npx @modelcontextprotocol/inspector python -m mcp_server.server

# Opens browser at http://localhost:6274 with tools panel
```

#### Claude Desktop Integration

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

### Manual workflow

If you prefer to run steps manually:

```bash
# Start services
docker compose up -d

# Apply migrations
docker compose exec backend alembic upgrade head

# Load fixtures
docker compose exec backend python -m scripts.seed_fixtures

# Run demo
docker compose exec backend python -m scripts.demo_kernel
```

### Replay (policy tuning without production risk)

Replay is the core development and pilot workflow:

import historical signals (CSV)

evaluate against current policy set

generate exceptions deterministically

tune thresholds and compare before/after

export evidence packs for decisions

```bash
# Example; implement in /replay
docker compose exec core bash -lc "python -m replay.run --pack treasury --from 2025-01-01 --to 2025-03-31"
``` 
### Product doctrine (non-negotiable)

Deterministic core: policy evaluation, exceptioning, and evidence packs are code, testable, replayable.

No recommendations in the decision layer: options are symmetric; user owns trade-offs.

One-screen commitment surface: no scrolling, no rabbit holes, no “UX-washing”.

Uncertainty is visible: confidence gaps and unknowns are first-class.

Memory is not logging: decisions link to evidence and outcomes; the graph compounds.

### Roadmap (high level)
#### ✅ Sprint 1: Kernel vertical slice (end-to-end loop) — COMPLETE

- ✅ Policy versioning with temporal validity
- ✅ Signal ingestion with provenance
- ✅ Deterministic evaluator with input hashing
- ✅ Exception engine with fingerprint deduplication
- ✅ One-screen decision UI (symmetric options, no recommendations)
- ✅ Immutable decision log with rationale/assumptions
- ✅ Evidence pack generation and export
- ✅ Treasury pack with sample policies
- ✅ Full Docker Compose setup (postgres + backend + frontend)

#### ✅ Sprint 2: Packs + replay (pilot-grade) + AI thin-slice — COMPLETE

- ✅ Treasury + Wealth packs (8 signal types, 8 policies each)
- ✅ CSV ingestion with SHA256 provenance tracking
- ✅ Replay harness with isolated namespaces + determinism verification
- ✅ Replay comparison tools (before/after policy changes)
- ✅ Exception budgets + metrics dashboard
- ✅ MCP v0 (read-only tools for AI agent integration)
- ✅ NarrativeAgent v0 (grounded memos with evidence references)
- ✅ Evals v0 (CI gate - fails on unsupported claims)
- ✅ Comprehensive test suite (187 tests)

#### ✅ Sprint 3: Agentic coprocessor (portfolio-grade AI engineering) — COMPLETE

- ✅ MCP write tools with approval gates + audit events
- ✅ IntakeAgent (unstructured → candidate signals with provenance + source spans)
- ✅ PolicyDraftAgent (natural language → policy drafts with test scenarios)
- ✅ Approval queue with human-in-the-loop gating
- ✅ Agent tracing viewer (runs → tool calls → audit events)
- ✅ Expanded eval suites (extraction, regression, policy draft) + CI gates
- ✅ Comprehensive test suite (302 tests)

### Contributing

This repo is early-stage and moving fast. Contributions are welcome:

improvements to policy schemas and evaluators

replay harness features (imports, comparisons, metrics)

UI rigor (one-screen exception surface)

connectors (read-only first)

Please open an issue first for non-trivial changes.

### License

MIT (see LICENSE).

### Disclaimer

Governance OS is decision-support tooling. It does not provide financial, investment, tax, or legal advice.

