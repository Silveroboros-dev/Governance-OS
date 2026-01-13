# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Governance OS is a policy-driven coordination layer for high-stakes professional work (starting with Corporate Treasury and Wealth Management). It converts continuous signals into deterministic policy evaluations, raises exceptions only when human judgment is required, and produces audit-grade evidence packs.

**Core loop:** Signal → Policy Evaluation → Exception → Decision → Evidence/Outcome

## Architecture Principles (Non-Negotiable)

### Deterministic Governance Kernel
The following components MUST remain deterministic, testable, and replayable:
- Signal ingestion validation and canonicalization
- Policy evaluation (same inputs → same outputs)
- Exception generation and deduplication
- Decision logging (immutable)
- Evidence pack generation

If the system cannot be replayed against the same dataset with identical results, it's a regression.

### AI Safety Boundaries
The kernel is deterministic. LLMs are optional coprocessors and never the source of truth for policy evaluation, escalation, or evidence.

**Allowed LLM usage:**
- Extracting candidate structured signals from unstructured inputs (with provenance + confidence + source spans)
- Drafting narratives from existing evidence graph (grounded to evidence IDs, never source of truth)
- Policy authoring assistance (human-approved only)

**Not allowed:**
- Policy evaluation or severity/escalation decisions
- "Recommended option" in the decision UI
- Silent writes without approvals/audit events

### UI Doctrine
- **No recommendations in decision layer:** Options are symmetric; the UI must not rank, highlight defaults, or nudge choices
- **One-screen commitment surface:** No scrolling, no drilldowns as default path
- **Uncertainty is first-class:** Confidence gaps and unknowns must remain visible and explicit

## Repository Structure

```
/core         FastAPI backend (deterministic governance kernel)
/ui           Next.js frontend (one-screen exception UI + supporting views)
/db           Migrations, schema, seed hooks
/packs        Domain packs (treasury, wealth): templates + fixtures + vocabulary
/replay       Replay harness: CSV import + scenario runner

# AI engineering layer (Sprint 2+)
/mcp          MCP server exposing kernel tools (read-only v0, gated writes later)
/coprocessor  Agents + tools + prompts + schemas + traces
/evals        Datasets + goldens + eval runner (CI-gated)
```

## Key Domain Concepts

- **Policy / PolicyVersion**: Explicit, versioned rules with change control
- **Signal**: Timestamped facts with provenance (source, reliability)
- **Evaluation**: Deterministic result of applying policy to signals
- **Exception**: Interruption when judgment is required (deduped, severity-tagged)
- **Decision**: Immutable commitment with rationale + assumptions
- **AuditEvent**: Append-only trail of meaningful state changes
- **Evidence Pack**: Deterministic bundle answering "why did we do this?"

## Development Commands

### Local setup
```bash
docker compose up --build
```

### Tests
```bash
# Backend (when implemented)
pytest

# Frontend (when implemented)
npm test
```

### Kernel demo (when implemented)
```bash
make demo-kernel
```

### MCP server (Sprint 2+)
```bash
make mcp
```

### Narrative agent (Sprint 2+)
```bash
make narrative EXCEPTION_ID=<id>
```

### Evals (Sprint 2+)
```bash
make evals  # Must pass
```

### Database migrations (when implemented)
```bash
docker compose exec core bash -lc "alembic upgrade head"
```

### Load fixtures (when implemented)
```bash
docker compose exec core bash -lc "python -m replay.seed_fixtures"
```

### Replay workflow (policy tuning)
```bash
# When implemented in /replay
docker compose exec core bash -lc "python -m replay.run --pack treasury --from 2025-01-01 --to 2025-03-31"
```

## Domain Packs

Treasury and Wealth are implemented as **packs** (configuration), not forks. Each pack contains:
- Signal types
- Policy templates
- Option templates
- UI copy / vocabulary
- Fixtures for demos and replay

## Development Guidelines

### When contributing code:
1. Preserve determinism for all kernel components (evaluator, exceptioning, evidence)
2. Never add recommendations, rankings, or defaults to the decision surface
3. Keep commitment UI to one screen (no scrolling)
4. Make uncertainty visible (don't "clean up" confidence gaps)
5. Ensure replayability: same inputs must produce same outputs

### For AI/LLM features (Sprint 2+):
1. All agent actions must go through tool contracts (MCP)
2. Agent outputs must be schema-validated
3. Narrative outputs must be grounded to evidence IDs
4. Add evals that fail CI on hallucinations or unsupported claims
5. Never let LLMs make policy decisions or escalation judgments

### Testing requirements:
- All kernel features must have determinism tests (replay with same inputs)
- AI features must have faithfulness evals (zero unsupported claims)
- Schema validation for all structured outputs
- Audit trail verification

## API Access (when implemented)

- UI: http://localhost:3000
- API: http://localhost:8000/docs

## Current Development Status

This is an early-stage repository. The planned implementation follows this roadmap:

**Sprint 1:** Deterministic governance kernel (policy → evaluation → exception → decision → evidence)

**Sprint 2:** Domain packs + replay harness + thin-slice AI layer (MCP read-only, NarrativeAgent v0, Evals v0)

**Sprint 3:** Full agentic coprocessor (MCP write tools, IntakeAgent, tracing viewer, expanded evals)
