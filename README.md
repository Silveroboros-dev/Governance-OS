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
/core FastAPI backend (kernel services)
/ui Next.js frontend (one-screen exception UI + supporting views)
/db Migrations, schema, seed hooks
/packs Domain packs (treasury, wealth): templates + fixtures + vocab
/replay Replay harness: CSV import + scenario runner

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
- Docker + Docker Compose
- Node.js (if running UI outside Docker)
- Python 3.11+ (if running core outside Docker)

### Run everything
```bash
docker compose up --build
```

### Apply migrations (if not automated)
# Example; adjust to your migration tool (e.g., Alembic)
docker compose exec core bash -lc "alembic upgrade head"

### Load fixtures (Treasury + Wealth)
# Example command; implement a real seed entrypoint in /core or /replay
docker compose exec core bash -lc "python -m replay.seed_fixtures"


### Then open:

UI: http://localhost:3000

API: http://localhost:8000/docs

### Replay (policy tuning without production risk)

Replay is the core development and pilot workflow:

import historical signals (CSV)

evaluate against current policy set

generate exceptions deterministically

tune thresholds and compare before/after

export evidence packs for decisions

# Example; implement in /replay
docker compose exec core bash -lc "python -m replay.run --pack treasury --from 2025-01-01 --to 2025-03-31"

### Product doctrine (non-negotiable)

Deterministic core: policy evaluation, exceptioning, and evidence packs are code, testable, replayable.

No recommendations in the decision layer: options are symmetric; user owns trade-offs.

One-screen commitment surface: no scrolling, no rabbit holes, no “UX-washing”.

Uncertainty is visible: confidence gaps and unknowns are first-class.

Memory is not logging: decisions link to evidence and outcomes; the graph compounds.



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

