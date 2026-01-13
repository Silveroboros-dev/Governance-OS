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

**IMPORTANT: Test Database Configuration**

Tests are configured to run **locally on the host machine**, NOT inside Docker containers. This is intentional:

- **Test database**: `postgresql://govos:local_dev_password@localhost:5432/governance_os_test`
- **Why**: Tests need fast setup/teardown with database fixtures, which is easier outside containers
- **Consequence**: You MUST have PostgreSQL accessible at `localhost:5432` (the docker-compose postgres container exposes this port)

**Running tests:**

```bash
# 1. Ensure docker-compose postgres is running (provides localhost:5432)
docker compose up -d postgres

# 2. Install Python dependencies locally (if not already done)
pip install -r core/requirements.txt

# 3. Run tests from host machine (NOT inside Docker)
pytest core/tests/ -v

# 4. Run only critical determinism tests
pytest core/tests/test_determinism.py -v -m critical

# Frontend tests (when implemented)
npm test
```

**Common mistake to avoid:**
- ❌ Running `docker compose exec backend pytest` will FAIL because the backend container tries to connect to `localhost` which is its own container, not the postgres container
- ✅ Run `pytest core/tests/` from your host machine with postgres container running

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

## Troubleshooting

### Tests failing with "connection refused" to localhost:5432

**Problem:** Tests are trying to connect to localhost but getting connection refused.

**Cause:** Tests are configured to run on the host machine (NOT inside Docker), and they expect PostgreSQL at `localhost:5432`.

**Solution:**
```bash
# 1. Ensure postgres container is running
docker compose up -d postgres

# 2. Verify postgres is accessible
docker compose ps | grep postgres

# 3. Run tests from HOST machine (not inside container)
pytest core/tests/ -v

# DON'T DO THIS (will fail):
docker compose exec backend pytest  # ❌ Wrong: tries to connect from inside container
```

### SQLAlchemy enum errors: "invalid input value for enum"

**Problem:** Database rejects enum values like "ACTIVE" instead of "active".

**Cause:** Python enum values are uppercase (e.g., `PolicyStatus.ACTIVE = "active"`), but SQLAlchemy was sending the enum name instead of the value.

**Solution:** All SQLAlchemy enum columns must use `values_callable`:
```python
# Correct:
status = Column(SQLEnum(PolicyStatus, name="policy_status",
                       values_callable=lambda x: [e.value for e in x]),
               nullable=False)

# Wrong (sends "ACTIVE" instead of "active"):
status = Column(SQLEnum(PolicyStatus, name="policy_status"), nullable=False)
```

### Alembic migration fails with "type already exists"

**Problem:** Migration creates enum types manually, then SQLAlchemy tries to create them again.

**Cause:** Manual `CREATE TYPE` statements in migration + SQLAlchemy auto-creating types.

**Solution:** Use `create_type=False` in migration enum references:
```python
# In migration file:
# 1. Create enums manually first
op.execute("CREATE TYPE policy_status AS ENUM ('draft', 'active', 'archived');")

# 2. Then reference with create_type=False
sa.Column('status',
         postgresql.ENUM('draft', 'active', 'archived',
                        name='policy_status', create_type=False),
         nullable=False)
```

### Circular foreign key relationship errors

**Problem:** SQLAlchemy complains about ambiguous foreign keys between `Decision` and `EvidencePack`.

**Cause:** Both tables reference each other creating a circular dependency.

**Solution:** Use unidirectional relationships only:
```python
# In EvidencePack model:
decision = relationship("Decision", foreign_keys="[EvidencePack.decision_id]")

# In Decision model:
# Don't add back-reference - access via EvidencePack.decision instead
```

### Docker build fails with "COPY path not found"

**Problem:** Dockerfile can't find files to copy (e.g., `../packs not found`).

**Cause:** Docker build context is wrong - using relative paths outside context.

**Solution:** Set build context to project root in docker-compose.yml:
```yaml
backend:
  build:
    context: .              # Root directory
    dockerfile: core/Dockerfile

# In Dockerfile, use paths relative to context root:
COPY core/ /app/core/
COPY packs/ /app/packs/
COPY db/ /app/db/
```

### Frontend can't reach backend API in Docker

**Problem:** Frontend running in Docker can't reach backend API. Browser shows network errors, CORS issues, or "Failed to fetch".

**Cause:** Confusion between **server-side** and **client-side** network contexts in containerized frontends.

**Key principle:** Frontend containers serve static assets to the browser. The **browser** then makes API calls from the user's machine - NOT from inside Docker. Docker internal hostnames (like `backend`, `api`, service names) are only resolvable within the Docker network, not from the browser.

**Common mistakes:**
```dockerfile
# WRONG - browser can't resolve Docker service names:
ENV NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
ENV REACT_APP_API_URL=http://api-service:3000

# CORRECT - browser accesses via exposed ports on localhost:
ENV NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV REACT_APP_API_URL=http://localhost:3000
```

**Framework-specific notes:**
- Next.js `NEXT_PUBLIC_*` vars are embedded at build time
- React/Vite `VITE_*` or `REACT_APP_*` vars are also build-time
- These run in the browser, so must use browser-accessible URLs

**When to use Docker hostnames:**
- Server-side API routes (Next.js API routes, SSR data fetching)
- Backend-to-backend communication
- Database connections from backend

**When to use localhost:**
- Any URL that ends up in browser JavaScript
- Environment variables with `PUBLIC`, `NEXT_PUBLIC_`, `VITE_`, `REACT_APP_` prefixes
