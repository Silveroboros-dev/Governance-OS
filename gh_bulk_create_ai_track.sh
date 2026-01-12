#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Governance-OS: Add Sprint 2 AI thin-slice + Sprint 4 AI track
# Requires: gh, jq
# Usage:
#   chmod +x ./gh_bulk_create_ai_track.sh
#   ./gh_bulk_create_ai_track.sh
#
# Optional:
#   FULL_REPO="owner/Governance-OS" ./gh_bulk_create_ai_track.sh
# ============================================================

require_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1"; exit 1; }; }
require_cmd gh
require_cmd jq

FULL_REPO="${FULL_REPO:-}"
if [[ -z "${FULL_REPO}" ]]; then
  FULL_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
fi
if [[ -z "${FULL_REPO}" ]]; then
  echo "ERROR: Could not detect repo. Run inside the repo or set FULL_REPO=owner/Governance-OS"
  exit 1
fi

echo "Using repo: ${FULL_REPO}"

label_exists() {
  local name="$1"
  gh api "repos/${FULL_REPO}/labels?per_page=100" --jq ".[] | select(.name==\"${name}\") | .name" | grep -q "^${name}$"
}
ensure_label() {
  local name="$1"; local color="$2"; local description="$3"
  if label_exists "${name}"; then echo "Label exists: ${name}"; return; fi
  gh label create "${name}" --repo "${FULL_REPO}" --color "${color}" --description "${description}" >/dev/null
  echo "Created label: ${name}"
}

ensure_milestone() {
  local title="$1"; local description="$2"
  if gh api "repos/${FULL_REPO}/milestones?state=all&per_page=100" --jq ".[] | select(.title==\"${title}\")" | jq -e . >/dev/null 2>&1; then
    echo "Milestone exists: ${title}"
    return
  fi
  gh api -X POST "repos/${FULL_REPO}/milestones" -f title="${title}" -f description="${description}" >/dev/null
  echo "Created milestone: ${title}"
}

issue_exists_by_title() {
  local title="$1"
  local found
  found="$(gh issue list --repo "${FULL_REPO}" --state all --search "in:title \"${title}\"" --json title --jq '.[].title' || true)"
  grep -Fxq "${title}" <<< "${found}"
}

create_issue() {
  local title="$1"; local milestone="$2"; local labels_csv="$3"; local body="$4"
  if issue_exists_by_title "${title}"; then echo "Issue exists (skipping): ${title}"; return; fi
  local tmp; tmp="$(mktemp)"
  printf "%s\n" "${body}" > "${tmp}"
  gh issue create --repo "${FULL_REPO}" --title "${title}" --milestone "${milestone}" --label "${labels_csv}" --body-file "${tmp}" >/dev/null
  rm -f "${tmp}"
  echo "Created issue: ${title}"
}

# ---------- ensure milestones ----------
# (Sprint 1 & 2 may already exist from your first script; this will skip if so.)
ensure_milestone "Sprint 2" "Domain packs + replay harness (pilot-grade read-only), plus AI thin-slice (MCP read-only + grounded narratives + evals)."
ensure_milestone "Sprint 4" "Agentic coprocessor + MCP write-tools with gates + tracing + eval suites + safety controls (portfolio-grade AI engineering)."

# ---------- ensure labels (adds AI/MCP specific areas) ----------
ensure_label "area/ai"  "FF7B72" "LLM/agent coprocessor, prompts, evals"
ensure_label "area/mcp" "A371F7" "MCP server + tool contracts"
ensure_label "type/eval" "1F6FEB" "Evaluation harness / datasets"
# If your repo already has priority/type/area labels from the first script, we don't touch them.
# But to be safe, ensure these exist too (no harm if already there).
ensure_label "priority/P0" "B60205" "Must ship"
ensure_label "priority/P1" "D93F0B" "Important"
ensure_label "type/feature" "0E8A16" "Product feature"
ensure_label "type/chore"   "6A737D" "Maintenance / tooling"
ensure_label "type/bug"     "D73A4A" "Bug / reliability"
ensure_label "area/backend" "1D76DB" "Backend services"
ensure_label "area/frontend" "5319E7" "Frontend UI"
ensure_label "area/replay"  "FBCA04" "Replay harness / simulation"
ensure_label "area/devops"  "0B3D91" "DevOps / deployment"

# ============================================================
# Sprint 2 — AI thin-slice track (small, safe, portfolio-relevant)
# ============================================================

create_issue "MCP server v0 (read-only kernel tools)" "Sprint 2" "priority/P0,type/feature,area/mcp,area/backend" "$(cat <<'EOF'
## Goal
Expose the governance kernel via MCP with **read-only** tools so agents can operate safely.

## Scope (read-only)
- `list_exceptions(...)`
- `get_exception(exception_id)`
- `get_evidence_pack(exception_id)` (or by evidence_pack_id)
- `list_policies()`
- `get_policy_version(policy_id, at_timestamp)`

## Non-goals
- No write tools in v0
- No execution actions

## Acceptance criteria
- [ ] MCP server runs locally and is documented
- [ ] Tool schemas are strict (input/output JSON schemas)
- [ ] Tools call existing APIs/services (single source of truth)
- [ ] All MCP tool calls are logged with request/response metadata (no secrets)
EOF
)"

create_issue "NarrativeAgent v0 (grounded memo from evidence IDs)" "Sprint 2" "priority/P0,type/feature,area/ai" "$(cat <<'EOF'
## Goal
Generate a CFO/board-grade memo draft **strictly grounded** to the evidence graph.

## Inputs
- exception_id (or evidence pack id)
- memo template type (treasury/wealth)

## Output (hard constraints)
- Every factual claim must cite an evidence ID (signal/evaluation/policy_version/decision)
- If the agent cannot ground a claim, it must omit it (no hallucinations)

## Acceptance criteria
- [ ] CLI or endpoint: `narrative_agent --exception <id> --template <...>`
- [ ] Output includes citations to evidence IDs inline or as footnotes
- [ ] Includes a “Known unknowns / assumptions” section
- [ ] Produces a deterministic “source map” (claim -> evidence IDs)
EOF
)"

create_issue "Evals v0 (narrative faithfulness + grounding)" "Sprint 2" "priority/P0,type/eval,area/ai" "$(cat <<'EOF'
## Goal
Prove the NarrativeAgent is not hallucinating and is properly grounded.

## Dataset
- 10–20 golden cases (treasury + wealth) using fixture evidence packs

## Metrics (minimum)
- Grounding coverage: % of claims with valid evidence IDs
- Unsupported claims: count of claims with no valid evidence ID (must be 0 to pass)
- Citation validity: cited IDs exist and match referenced content

## Acceptance criteria
- [ ] `evals/run_evals` command returns pass/fail
- [ ] CI job runs evals and fails on unsupported claims
- [ ] Eval output is machine-readable (JSON) and human-readable summary
EOF
)"

# ============================================================
# Sprint 4 — Full AI engineering track (agents, MCP write tools, traces, safety)
# ============================================================

create_issue "Coprocessor module scaffolding (agents/tools/schemas/prompts/traces)" "Sprint 4" "priority/P0,type/feature,area/ai" "$(cat <<'EOF'
## Goal
Make the AI layer a first-class, reviewable, testable subsystem.

## Required layout (suggested)
- /coprocessor/agents
- /coprocessor/tools
- /coprocessor/schemas
- /coprocessor/prompts
- /coprocessor/traces
- /coprocessor/evals (or /evals)

## Acceptance criteria
- [ ] Prompts are versioned files, not embedded strings
- [ ] Input/output schemas exist for each agent
- [ ] Tracing interface exists (structured events)
EOF
)"

create_issue "MCP server v1 (write tools with approval gates + audit events)" "Sprint 4" "priority/P0,type/feature,area/mcp,area/backend" "$(cat <<'EOF'
## Goal
Add **write** MCP tools that change system state, but only through explicit governance gates.

## Write tools (examples)
- `create_policy_draft(...)`
- `propose_policy_version(...)` (draft only)
- `ingest_candidate_signals(...)` (stores as 'candidate' with provenance)
- `promote_candidate_signal(...)` (requires approval)
- `request_decision(exception_id, options)` (no recommendation)

## Hard requirements
- All writes produce audit events
- Approval gates enforced (role-based)
- Safe failure modes (no partial silent writes)

## Acceptance criteria
- [ ] Write tools require auth context + role
- [ ] Every tool call is traceable to user/agent identity
- [ ] Rate limits and idempotency keys supported
EOF
)"

create_issue "IntakeAgent v1 (unstructured docs → candidate signals w/ provenance)" "Sprint 4" "priority/P0,type/feature,area/ai" "$(cat <<'EOF'
## Goal
Reduce tedious workload: convert unstructured inputs (emails/PDF/text) into structured *candidate* signals.

## Inputs
- raw text OR file reference (local fixtures at first)
- pack context (treasury/wealth)

## Output
- candidate signals + provenance + confidence
- extraction notes + source spans (where the data came from)

## Acceptance criteria
- [ ] Can run on fixture inputs without external dependencies
- [ ] Produces candidate signals, not live signals (promotion requires approval)
- [ ] Stores source spans / citations to original text
- [ ] Works for at least 2 treasury and 2 wealth document types
EOF
)"

create_issue "PolicyDraftAgent v1 (policy text → draft PolicyVersion + diff)" "Sprint 4" "priority/P1,type/feature,area/ai" "$(cat <<'EOF'
## Goal
Accelerate policy authoring while preserving human ownership.

## Inputs
- human policy text / limits / SOPs
- existing policy versions (optional)

## Output
- draft PolicyVersion JSON (schema-valid)
- diff vs current version + rationale for changes

## Acceptance criteria
- [ ] Generates schema-valid draft PolicyVersion
- [ ] Produces a diff view (fields changed)
- [ ] Never publishes automatically (human must approve/publish)
EOF
)"

create_issue "NarrativeAgent v1 (multi-template memos + strict evidence grounding)" "Sprint 4" "priority/P1,type/feature,area/ai" "$(cat <<'EOF'
## Goal
Upgrade memo generation to support multiple templates while staying strictly grounded.

## Templates (minimum)
- Treasury: liquidity exception memo
- Wealth: suitability/privacy exception memo

## Acceptance criteria
- [ ] Supports templates and consistent tone
- [ ] Claim → evidence ID mapping is preserved
- [ ] Includes uncertainties and assumptions explicitly
- [ ] Produces both short and long versions (configurable)
EOF
)"

create_issue "Agent tracing + telemetry (structured traces + storage + viewer stub)" "Sprint 4" "priority/P0,type/feature,area/ai,area/backend" "$(cat <<'EOF'
## Goal
Make agent behavior observable and debuggable (portfolio-grade).

## Trace events (minimum)
- tool_call_started / tool_call_finished
- prompt_version_used
- schema_validation_pass/fail
- grounding_check_pass/fail
- safety_gate_triggered (blocked write, redaction, rate limit)

## Acceptance criteria
- [ ] Traces stored (DB table or file-based in MVP)
- [ ] Correlation
