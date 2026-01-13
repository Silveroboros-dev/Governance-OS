# Governance OS

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



### Planned (Sprint 1–2 focus)
- Deterministic governance kernel (policy → evaluation → exception → decision)
- Replay-first workflow (same inputs → same outputs)
- Evidence packs for defensibility and learning

### Planned (Sprint 2 thin-slice)
- **MCP server (read-only tools)** exposing kernel state safely  
- **NarrativeAgent v0**: drafts memos strictly grounded to evidence IDs  
- **Evals v0**: CI fails on unsupported claims (anti-hallucination gate)

### Planned (Sprint 3: portfolio-grade AI layer)
- MCP write tools with approval gates + audit events  
- IntakeAgent (unstructured → candidate signals w/ provenance + confidence + source spans)  
- Agent tracing viewer (runs → tool calls → audit events)  
- Expanded eval suites (extraction accuracy + faithfulness + kernel regression)

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
  /core FastAPI backend (deterministic governance kernel)
  /ui Next.js frontend (one-screen exception UI + supporting views)
  /db Migrations, schema, seed hooks
  /packs Domain packs (treasury, wealth): templates + fixtures + vocabulary
  /replay Replay harness: CSV import + scenario runner

  # AI engineering layer
  /mcp         MCP server exposing kernel tools (read-only v0, gated writes later)
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

---

## Quick start (local)

### Prerequisites
- Docker + Docker Compose (required)
- Python 3.11+ (optional, for local development)

### Run the system

```bash
# 1. Start services (postgres + backend)
make up

# 2. Load treasury fixtures (policies + sample signals)
make seed

# 3. Run kernel demo (full loop: signal → decision → evidence)
make demo-kernel
```

### Access the API

- **API Documentation:** http://localhost:8000/docs
- **API Base URL:** http://localhost:8000/api/v1
- **Health Check:** http://localhost:8000/health

### Common commands

```bash
make up           # Start all services
make down         # Stop all services
make logs         # View logs
make shell        # Open backend shell
make db           # Open postgres shell
make clean        # Remove all containers and volumes
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
#### Sprint 1: Kernel vertical slice (end-to-end loop)

policy versioning

signal ingestion

deterministic evaluator

exception engine + dedupe

one-screen exception UI

immutable decision log

evidence pack export

#### Sprint 2: Packs + replay (pilot-grade) + AI thin-slice

treasury + wealth packs

CSV ingestion + provenance

replay namespace + comparisons

exception budgets + metrics

MCP v0 (read-only tools)

NarrativeAgent v0 (grounded memos)

Evals v0 (fail on unsupported claims)

#### Sprint 3: Agentic coprocessor (portfolio-grade AI engineering)

MCP write tools with approval gates + audit events

IntakeAgent (unstructured → candidate signals with provenance + source spans)

tracing viewer (agent runs → tool calls → audit events)

expanded eval suites + CI gates

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

