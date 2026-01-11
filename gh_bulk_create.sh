#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Bulk create milestones + labels + issues for governance_os
# Requires: gh, jq
# Usage:
#   chmod +x ./gh_bulk_create.sh
#   ./gh_bulk_create.sh
#
# Optional:
#   FULL_REPO="Silveroboros-dev/Governance-OS" ./gh_bulk_create.sh
# ============================================================

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1"; exit 1; }
}

require_cmd gh
require_cmd jq

# Detect repo (prefer env override)
FULL_REPO="${FULL_REPO:-}"
if [[ -z "${FULL_REPO}" ]]; then
  FULL_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
fi
if [[ -z "${FULL_REPO}" ]]; then
  echo "ERROR: Could not detect repo. Run inside the repo or set FULL_REPO=owner/Governance-OS"
  exit 1
fi

if [[ "${FULL_REPO}" != */Governance-OS ]]; then
  echo "WARNING: Detected repo is '${FULL_REPO}', expected something ending with '/Governance-OS'."
  echo "If this is wrong, re-run with: FULL_REPO='owner/Governance-OS' ./gh_bulk_create.sh"
fi

echo "Using repo: ${FULL_REPO}"

# ---------- helpers ----------
milestone_exists() {
  local title="$1"
  gh api "repos/${FULL_REPO}/milestones?state=all&per_page=100" \
    --jq ".[] | select(.title==\"${title}\") | .number" >/dev/null
}

ensure_milestone() {
  local title="$1"
  local description="$2"

  if gh api "repos/${FULL_REPO}/milestones?state=all&per_page=100" --jq ".[] | select(.title==\"${title}\")" | jq -e . >/dev/null 2>&1; then
    echo "Milestone exists: ${title}"
    return
  fi

  gh api -X POST "repos/${FULL_REPO}/milestones" \
    -f title="${title}" \
    -f description="${description}" >/dev/null
  echo "Created milestone: ${title}"
}

label_exists() {
  local name="$1"
  gh api "repos/${FULL_REPO}/labels?per_page=100" --jq ".[] | select(.name==\"${name}\") | .name" | grep -q "^${name}$"
}

ensure_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  if label_exists "${name}"; then
    echo "Label exists: ${name}"
    return
  fi

  # gh label create requires a color
  gh label create "${name}" --repo "${FULL_REPO}" --color "${color}" --description "${description}" >/dev/null
  echo "Created label: ${name}"
}

issue_exists_by_title() {
  local title="$1"
  # Search only OPEN issues to avoid duplicates; change if you want include closed.
  local found
  found="$(gh issue list --repo "${FULL_REPO}" --state all --search "in:title \"${title}\"" --json title --jq '.[].title' || true)"
  grep -Fxq "${title}" <<< "${found}"
}

create_issue() {
  local title="$1"
  local milestone="$2"
  local labels_csv="$3"
  local body="$4"

  if issue_exists_by_title "${title}"; then
    echo "Issue exists (skipping): ${title}"
    return
  fi

  local tmp
  tmp="$(mktemp)"
  printf "%s\n" "${body}" > "${tmp}"

  # gh issue create accepts comma-separated labels
  gh issue create \
    --repo "${FULL_REPO}" \
    --title "${title}" \
    --milestone "${milestone}" \
    --label "${labels_csv}" \
    --body-file "${tmp}" >/dev/null

  rm -f "${tmp}"
  echo "Created issue: ${title}"
}

# ---------- milestones ----------
ensure_milestone "Sprint 1" "Governance kernel vertical slice (end-to-end loop)."
ensure_milestone "Sprint 2" "Domain packs + replay harness (pilot-grade read-only)."

# ---------- labels ----------
# priority
ensure_label "priority/P0" "B60205" "Must ship"
ensure_label "priority/P1" "D93F0B" "Important"

# type
ensure_label "type/feature" "0E8A16" "Product feature"
ensure_label "type/chore"   "6A737D" "Maintenance / tooling"
ensure_label "type/bug"     "D73A4A" "Bug / reliability"

# area
ensure_label "area/backend" "1D76DB" "Backend services"
ensure_label "area/frontend" "5319E7" "Frontend UI"
ensure_label "area/db"      "0052CC" "Database / migrations"
ensure_label "area/devops"  "0B3D91" "DevOps / deployment"
ensure_label "area/replay"  "FBCA04" "Replay harness / simulation"

# ============================================================
# Sprint 1 issues
# ============================================================

create_issue "Repo + project skeleton" "Sprint 1" "priority/P0,type/chore,area/devops" "$(cat <<'EOF'
## Goal
Create monorepo structure and baseline documentation.

## Acceptance criteria
- [ ] Repo has folders: `core/`, `ui/`, `db/`, `packs/`, `replay/`
- [ ] Root `README.md` includes run steps + folder responsibilities
- [ ] `.gitignore` appropriate for Python/Node/Docker
EOF
)"

create_issue "Dev environment (Docker Compose)" "Sprint 1" "priority/P0,type/feature,area/devops" "$(cat <<'EOF'
## Goal
One command boots local environment.

## Depends on
- Repo + project skeleton

## Acceptance criteria
- [ ] `docker compose up` starts Postgres + backend + frontend
- [ ] `.env.example` exists for both services
- [ ] Healthchecks or simple “ready” checks are present
EOF
)"

create_issue "Code quality gates (lint/format/test)" "Sprint 1" "priority/P1,type/chore,area/devops" "$(cat <<'EOF'
## Goal
Prevent slow drift while solo-building.

## Depends on
- Repo + project skeleton

## Acceptance criteria
- [ ] Backend: `lint`, `format`, `test` commands documented
- [ ] Frontend: `lint` and `format` commands documented
- [ ] CI stub (GitHub Actions) runs at least lint + unit tests
EOF
)"

create_issue "Database migrations baseline" "Sprint 1" "priority/P0,type/feature,area/db" "$(cat <<'EOF'
## Goal
Reliable schema evolution from day 1.

## Depends on
- Dev environment (Docker Compose)

## Acceptance criteria
- [ ] Migration tool configured (Alembic or equivalent)
- [ ] First migration applies cleanly to a fresh DB
- [ ] `make migrate` (or similar) documented
EOF
)"

create_issue "Core schema v1 (tables + FK graph)" "Sprint 1" "priority/P0,type/feature,area/db" "$(cat <<'EOF'
## Goal
Implement kernel objects in Postgres.

## Depends on
- Database migrations baseline

## Tables (v1)
- `policy`
- `policy_version`
- `signal`
- `evaluation`
- `exception`
- `decision`
- `audit_event` (append-only)

## Acceptance criteria
- [ ] FK graph enforces: policy → policy_version; exception links to policy_version; decision links to exception
- [ ] `audit_event` is append-only by application logic (no updates)
- [ ] Indexes for lookup by `entity_id`, `created_at`, `status`
EOF
)"

create_issue "Backend domain models + repository layer" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Typed models and DB access patterns.

## Depends on
- Core schema v1 (tables + FK graph)

## Acceptance criteria
- [ ] Typed models for each core table
- [ ] Repository functions with unit tests (CRUD minimal)
- [ ] DB errors handled cleanly (no raw stack traces)
EOF
)"

create_issue "Policy API (CRUD for policy metadata)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Create/read policy with ownership + scope.

## Depends on
- Backend domain models + repository layer

## Acceptance criteria
- [ ] Endpoints: create policy, get policy, list policies, update metadata
- [ ] Writes emit an `audit_event`
- [ ] Basic validation: name required, owner required
EOF
)"

create_issue "Policy versioning API (draft → publish)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Immutable published versions + effective dating.

## Depends on
- Policy API (CRUD for policy metadata)

## Acceptance criteria
- [ ] Create draft version for a policy
- [ ] Publish version (published versions immutable)
- [ ] Fetch effective version at timestamp
- [ ] Audit events: `policy_version_drafted`, `policy_version_published`
EOF
)"

create_issue "Signal ingestion API (JSON batch)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Ingest canonical signals with provenance.

## Depends on
- Backend domain models + repository layer

## Acceptance criteria
- [ ] POST single + batch signals
- [ ] Validates: timestamp, source, entity_id, metric/value shape
- [ ] Stores provenance fields (source type, reliability)
- [ ] Audit event per batch import
EOF
)"

create_issue "Evaluator v1 (deterministic threshold rules)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Convert signals into evaluations against policy versions deterministically.

## Depends on
- Policy versioning API (draft → publish)
- Signal ingestion API (JSON batch)

## Acceptance criteria
- [ ] Deterministic evaluation result: `inside|soft_breach|hard_breach|ambiguous`
- [ ] Evaluation stores policy_version reference + rationale string
- [ ] Unit tests cover threshold edge cases (==, boundary, missing metric)
EOF
)"

create_issue "Exception engine v1 (breach → exception + dedupe)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Create actionable exceptions, not alert spam.

## Depends on
- Evaluator v1 (deterministic threshold rules)

## Acceptance criteria
- [ ] Hard breach → CRITICAL exception
- [ ] Soft breach → MATERIAL when sustained (N events or time window)
- [ ] Dedupe by (policy_version, entity_id, open status)
- [ ] Audit event: `exception_raised`
EOF
)"

create_issue "Decision API (commitment + immutability)" "Sprint 1" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Record accountable decisions with rationale.

## Depends on
- Exception engine v1 (breach → exception + dedupe)

## Acceptance criteria
- [ ] Create decision linked to exception
- [ ] Required: option_id/choice, rationale, assumptions (can be empty list)
- [ ] Decisions immutable (no edit); supersede by creating new decision
- [ ] Audit event: `decision_confirmed`
EOF
)"

create_issue "Evidence pack generator v1 (JSON bundle)" "Sprint 1" "priority/P1,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Export “why did we do this?” bundle deterministically.

## Depends on
- Decision API (commitment + immutability)

## Acceptance criteria
- [ ] Export includes: exception, decision, policy_version(s), top signals, evaluations, audit refs
- [ ] Same inputs → same output (deterministic ordering)
- [ ] Endpoint returns a downloadable JSON
EOF
)"

create_issue "UI: Exception list + one-screen exception card" "Sprint 1" "priority/P0,type/feature,area/frontend" "$(cat <<'EOF'
## Goal
The product surface (no scrolling, no chat).

## Depends on
- Exception engine v1 (breach → exception + dedupe)
- Decision API (commitment + immutability)

## Acceptance criteria
- [ ] List open exceptions
- [ ] Clicking opens one-screen exception card
- [ ] Card shows: header, what changed, impacted policy, uncertainty, symmetric options, decision capture
- [ ] Confirm disabled until rationale entered
- [ ] Confirm updates exception status and persists decision
EOF
)"

create_issue "Seed fixtures + smoke demo (Treasury + Wealth)" "Sprint 1" "priority/P1,type/feature,area/replay" "$(cat <<'EOF'
## Goal
One command seeds and demonstrates end-to-end loop.

## Depends on
- UI: Exception list + one-screen exception card
- Evidence pack generator v1 (JSON bundle)

## Acceptance criteria
- [ ] Fixtures exist in `packs/treasury/fixtures` and `packs/wealth/fixtures`
- [ ] A seed command loads policies + signals → produces exceptions
- [ ] Demo flow works: open exception → decide → export evidence pack
EOF
)"

# ============================================================
# Sprint 2 issues
# ============================================================

create_issue "Domain Pack contract (config interface)" "Sprint 2" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Two domains without forking code.

## Depends on
- Seed fixtures + smoke demo (Treasury + Wealth)

## Acceptance criteria
- [ ] Define `Pack` contract (signal types, policy templates, option templates, UI copy)
- [ ] Kernel loads pack config (no domain branching in core logic)
- [ ] UI renders pack-provided labels and options
EOF
)"

create_issue "Treasury pack v1 (config)" "Sprint 2" "priority/P0,type/feature,area/replay" "$(cat <<'EOF'
## Goal
Treasury vocabulary on the same kernel.

## Depends on
- Domain Pack contract (config interface)

## Acceptance criteria
- [ ] Signal types: liquidity_drop, concentration_drift, settlement_delay
- [ ] Policy templates: LiquidityBuffer, CounterpartyConcentration, SettlementSLA
- [ ] Options templates: override / funding_draw / freeze
- [ ] UI renders these templates correctly
EOF
)"

create_issue "Wealth pack v1 (config)" "Sprint 2" "priority/P0,type/feature,area/replay" "$(cat <<'EOF'
## Goal
Wealth vocabulary on the same kernel.

## Depends on
- Domain Pack contract (config interface)

## Acceptance criteria
- [ ] Signal types: suitability_drift, permission_risk, stress_event
- [ ] Policy templates: Suitability, Permissions, BadMarketProtocol triggers
- [ ] Options templates: rebalance / hold / comms_protocol / specialist_engage
- [ ] UI renders these templates correctly
EOF
)"

create_issue "CSV ingestion (canonical signal mapper)" "Sprint 2" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Pilot onboarding without deep integrations.

## Depends on
- Signal ingestion API (JSON batch)

## Acceptance criteria
- [ ] Upload CSV → validates → maps to canonical signals
- [ ] Stores mapping_version + provenance (source=file)
- [ ] Import report: rows ok/failed + error reasons
- [ ] Audit event: csv_import_completed
EOF
)"

create_issue "Replay runner v1 (time window → evaluations → exceptions)" "Sprint 2" "priority/P0,type/feature,area/replay" "$(cat <<'EOF'
## Goal
Fast tuning and credibility.

## Depends on
- CSV ingestion (canonical signal mapper)
- Evaluator v1 (deterministic threshold rules)
- Exception engine v1 (breach → exception + dedupe)

## Acceptance criteria
- [ ] Select pack + date range → run deterministically
- [ ] Uses “replay namespace” (separate from live) to avoid polluting prod data
- [ ] Produces exceptions viewable in UI
EOF
)"

create_issue "Exception timeline view (secondary screen)" "Sprint 2" "priority/P1,type/feature,area/frontend" "$(cat <<'EOF'
## Goal
Pilot-friendly triage and exploration after the commitment surface.

## Depends on
- Replay runner v1 (time window → evaluations → exceptions)

## Acceptance criteria
- [ ] Timeline/list by date with filters: severity, policy, entity
- [ ] Click opens same one-screen exception card
- [ ] Fast filter performance (indexes as needed)
EOF
)"

create_issue "Policy tuning workflow (draft → replay → compare)" "Sprint 2" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Close the learning loop without production risk.

## Depends on
- Policy versioning API (draft → publish)
- Replay runner v1 (time window → evaluations → exceptions)

## Acceptance criteria
- [ ] Create draft policy version
- [ ] Replay against same dataset with draft version
- [ ] Compare counts: exceptions_before vs exceptions_after
- [ ] Simple diff view available (can be minimal)
EOF
)"

create_issue "Exception budget controls + metrics" "Sprint 2" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Prevent alert fatigue (product survival).

## Depends on
- Exception timeline view (secondary screen)

## Acceptance criteria
- [ ] Configure budget per pack: max critical/week, max material/week
- [ ] Track: exception volume, decision latency, open exceptions
- [ ] Warning banner if budget exceeded
EOF
)"

create_issue "Minimal auth v1 (identity for decisions)" "Sprint 2" "priority/P1,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Attach decisions to real identities (audit realism).

## Depends on
- Decision API (commitment + immutability)

## Acceptance criteria
- [ ] Simple login or API token-based identity
- [ ] Decisions store `decision_maker`
- [ ] UI shows current user
EOF
)"

create_issue "Roles stub (Viewer / Decider / Approver)" "Sprint 2" "priority/P1,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Enable approval flows without heavy IAM.

## Depends on
- Minimal auth v1 (identity for decisions)

## Acceptance criteria
- [ ] Role assignment (config-based is fine)
- [ ] UI respects role for decision confirmation where required
EOF
)"

create_issue "Approval rule for hard overrides" "Sprint 2" "priority/P0,type/feature,area/backend" "$(cat <<'EOF'
## Goal
Governance enforcement.

## Depends on
- Roles stub (Viewer / Decider / Approver)
- Decision API (commitment + immutability)

## Acceptance criteria
- [ ] Decisions tagged as “hard override” require Approver role
- [ ] Audit records approver identity + timestamp
- [ ] UI blocks confirm if user lacks permission
EOF
)"

create_issue "Evidence pack export v2 (print-ready HTML or PDF)" "Sprint 2" "priority/P1,type/feature,area/backend" "$(cat <<'EOF'
## Goal
CFO/auditor readable output.

## Depends on
- Evidence pack generator v1 (JSON bundle)

## Acceptance criteria
- [ ] One-click export readable without tooling
- [ ] Includes: policy version, signals summary, decision rationale, timestamps
- [ ] Deterministic ordering
EOF
)"

create_issue "“Why did we do this?” trace view" "Sprint 2" "priority/P1,type/feature,area/frontend" "$(cat <<'EOF'
## Goal
Make accountability visceral.

## Depends on
- Evidence pack generator v1 (JSON bundle)
- UI: Exception list + one-screen exception card

## Acceptance criteria
- [ ] Trace view: exception → decision → policy version → top signals/evaluations
- [ ] Links to evidence pack
- [ ] No raw data dumps; concise and navigable
EOF
)"

create_issue "Idempotency + dedupe hardening" "Sprint 2" "priority/P0,type/bug,area/backend" "$(cat <<'EOF'
## Goal
Prevent duplicate signals/exceptions during imports and retries.

## Depends on
- CSV ingestion (canonical signal mapper)
- Exception engine v1 (breach → exception + dedupe)

## Acceptance criteria
- [ ] Signal ingestion supports idempotency keys
- [ ] Batch imports safe to re-run
- [ ] Exception dedupe stable under replay + batch
EOF
)"

create_issue "Observability + runbook (minimum viable)" "Sprint 2" "priority/P1,type/chore,area/devops" "$(cat <<'EOF'
## Goal
Solo ops survival.

## Depends on
- CSV ingestion (canonical signal mapper)
- Exception engine v1 (breach → exception + dedupe)
- Decision API (commitment + immutability)

## Acceptance criteria
- [ ] Structured logs for: ingestion, evaluation, exception creation, decision confirmation
- [ ] Minimal runbook: “If exceptions spike…”, “If imports fail…”, “If policy publish fails…”
- [ ] Basic error reporting (at least log aggregation)
EOF
)"

create_issue "Pilot demo scripts (Treasury + Wealth)" "Sprint 2" "priority/P1,type/chore,area/replay" "$(cat <<'EOF'
## Goal
Repeatable 3–5 minute demos that close deals.

## Depends on
- Exception budget controls + metrics
- Evidence pack export v2 (print-ready HTML or PDF)
- Exception timeline view (secondary screen)

## Acceptance criteria
- [ ] Treasury script: replay → exception → decision → evidence export → KPI snapshot
- [ ] Wealth script: replay → suitability/privacy exception → decision → evidence export → KPI snapshot
- [ ] Scripts stored as markdown in repo and reproducible
EOF
)"

echo "Done."
