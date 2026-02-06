# Decision Journey: How Governance OS Facilitates Human Judgment

This document explains how Governance OS presents exceptions to humans, captures decisions, and produces audit-grade evidence.

## Core Philosophy

**The kernel is deterministic. Humans decide.**

Governance OS:
- **DOES** surface when human judgment is required (exceptions)
- **DOES** present symmetric options with implications
- **DOES** require rationale for audit trail
- **DOES** generate evidence packs proving "why we did this"

Governance OS:
- **DOES NOT** recommend options or rank choices
- **DOES NOT** make policy decisions via LLM
- **DOES NOT** allow decisions without rationale
- **DOES NOT** permit modification after commitment

## Decision Flow Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DECISION FLOW                                         │
└──────────────────────────────────────────────────────────────────────────────┘

  Signal (BREACH)
        │
        ▼
┌──────────────────┐
│  Policy Engine   │  Evaluates signal against active policies
│  (Deterministic) │  Same inputs → Same evaluation result
└────────┬─────────┘
         │
         ▼ FAIL
┌──────────────────┐
│    Exception     │  Human judgment required
│   (Interrupt)    │  Deduplicated by fingerprint
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Decision UI    │  One-screen commitment surface
│  (Human Action)  │  Options presented SYMMETRICALLY
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Decision      │  IMMUTABLE record
│   (Committed)    │  Rationale required
└────────┬─────────┘
         │
         ├────────────────────────┐
         ▼                        ▼
┌──────────────────┐    ┌──────────────────┐
│  Evidence Pack   │    │ Narrative Memo   │
│ (Audit Bundle)   │    │ (Gemini Draft)   │
└──────────────────┘    └──────────────────┘
```

## Exception: The Interrupt

An **Exception** is raised when policy evaluation detects a condition requiring human judgment.

### Exception Properties

| Field | Purpose |
|-------|---------|
| `id` | Unique identifier |
| `fingerprint` | Deduplication hash (prevents duplicate exceptions) |
| `severity` | `critical`, `high`, `medium`, `low` |
| `status` | `open` → `resolved` (or `dismissed`) |
| `title` | Human-readable summary |
| `context` | Structured data for UI |
| `options` | Symmetric choices (no ranking!) |

### Fingerprint Deduplication

Exceptions are deduplicated using fingerprints:

```
fingerprint = SHA256(policy_id + exception_type + key_dimensions)
```

**Rules:**
- Same fingerprint while `status=open` → duplicate blocked
- Same fingerprint after `status=resolved` → can recur
- Prevents alert fatigue from repeated identical exceptions

### Severity Assignment

Severity comes from the **constraint registry**, not from LLM judgment:

```json
"severity_rules": {
  "default": "high",
  "escalation": [
    {"condition": "breach_percent > 50", "severity": "critical"},
    {"condition": "duration_hours > 24", "severity": "critical"}
  ]
}
```

This is **deterministic**: same payload + same rules = same severity.

## Options: Symmetric Choices

**Critical Design Principle:** Options are ALWAYS symmetric. The UI must not:
- Rank options
- Highlight defaults
- Show "recommended" badges
- Nudge toward any choice

### Option Structure

```json
{
  "id": "approve_temporary_increase",
  "label": "Approve Temporary Increase",
  "description": "Allow position to remain above limit for defined period",
  "implications": [
    "Increased market risk exposure",
    "Requires monitoring for duration",
    "May need board notification if critical"
  ]
}
```

### Example: Position Limit Breach Options

| Option | Description | Implications |
|--------|-------------|--------------|
| **Approve Temporary Increase** | Allow position to remain above limit | Increased risk, requires monitoring |
| **Require Immediate Reduction** | Mandate position reduction | Trading costs, reduces exposure |
| **Escalate to CFO** | Elevate to CFO for review | Delays resolution, higher accountability |

All three options are presented equally. The human decides based on context.

## Decision: The Commitment

A **Decision** is an immutable commitment that resolves an exception.

### Decision Properties

| Field | Required | Purpose |
|-------|----------|---------|
| `chosen_option_id` | Yes | Which option was selected |
| `rationale` | Yes (min 10 chars) | Why this choice was made |
| `assumptions` | No | Explicit assumptions |
| `decided_by` | Yes | Accountability |
| `decided_at` | Auto | Timestamp |

### Immutability

Decisions are **IMMUTABLE** after creation:
- No UPDATE operations allowed
- Enforced at ORM level AND database trigger level
- Creates accountability trail

```sql
-- Database trigger prevents updates
CREATE TRIGGER prevent_decision_update
BEFORE UPDATE ON decisions
FOR EACH ROW EXECUTE FUNCTION prevent_update();
```

### Rationale Requirement

Rationale is **required** and must be at least 10 characters:

```python
rationale: str = Field(..., min_length=10, description="Decision rationale (required)")
```

**Why?** Audit trail. Every decision must explain "why" for future reference.

### Hard Overrides

For decisions that override policy recommendations:

```python
class DecisionType(str, Enum):
    STANDARD = "standard"           # Normal decision flow
    HARD_OVERRIDE = "hard_override" # Overrides policy, requires approval
```

Hard overrides require:
- `approved_by` (user with Approver role)
- `approved_at` (timestamp)
- `approval_notes` (optional justification)

Database constraint ensures this:
```sql
CHECK (
  (is_hard_override = false) OR
  (approved_by IS NOT NULL AND approved_at IS NOT NULL)
)
```

## Evidence Pack: The Audit Bundle

After a decision is committed, an **Evidence Pack** is generated automatically.

### Evidence Pack Contents

```json
{
  "decision": {
    "id": "...",
    "chosen_option_id": "approve_temporary_increase",
    "rationale": "Market conditions justify temporary position increase",
    "assumptions": "Volatility will normalize within 24 hours",
    "decided_by": "treasury_manager",
    "decided_at": "2024-01-15T14:30:00Z"
  },
  "exception": {
    "title": "Position Limit Breach: EUR/USD",
    "severity": "high",
    "context": {...},
    "options": [...]
  },
  "evaluation": {
    "result": "fail",
    "details": {...}
  },
  "policy": {
    "name": "Position Limits Policy",
    "version_number": 3,
    "rule_definition": {...}
  },
  "signals": [
    {
      "signal_type": "position_limit_breach",
      "payload": {"asset": "EUR/USD", "current_position": 15000000, "limit": 10000000},
      "source": "risk_system",
      "reliability": "high"
    }
  ],
  "audit_trail": [...]
}
```

### Content Hash

Evidence packs have a deterministic content hash:

```python
content_hash = SHA256(json.dumps(evidence, sort_keys=True))
```

**Purpose:** Proves the evidence hasn't been tampered with.

### Export Formats

Evidence packs can be exported as:
- **JSON** - Machine-readable
- **HTML** - Standalone document
- **PDF** - Print-ready audit document

## Narrative Memo (Optional)

If `GOOGLE_API_KEY` is set, a **NarrativeAgent** (Gemini) drafts a human-readable memo.

### Key Constraints

The narrative is **grounded to evidence**:
- Every claim must reference an `evidence_id`
- No unsupported assertions allowed
- LLM drafts, evidence proves

```json
{
  "memo_type": "decision_brief",
  "summary": "Treasury approved temporary position limit increase for EUR/USD...",
  "claims": [
    {
      "text": "Position exceeded limit by 50%",
      "evidence_refs": ["sig_a1b2c3d4"],
      "confidence": 1.0
    }
  ]
}
```

### Failure Handling

If narrative generation fails:
- Evidence pack is still saved (complete without narrative)
- Warning logged, no exception raised
- Decision is valid regardless of narrative status

## UI Doctrine

### One-Screen Commitment Surface

The decision UI is designed for:
- **No scrolling** - Everything visible at once
- **No drilldowns** - No hidden context
- **Immediate action** - Clear commitment button

### Three-Column Layout

```
┌─────────────────┬─────────────────┬─────────────────┐
│     CONTEXT     │     OPTIONS     │    DECISION     │
├─────────────────┼─────────────────┼─────────────────┤
│ Impacted Policy │ Option 1        │ Rationale *     │
│ What Changed    │ Option 2        │ (required)      │
│ Uncertainty     │ Option 3        │                 │
│                 │                 │ Selected: ...   │
│                 │                 │ [Commit]        │
└─────────────────┴─────────────────┴─────────────────┘
```

### Uncertainty is First-Class

Low confidence or missing data is shown explicitly:

```
⚠ Uncertainty
• Signal "position_limit_breach" has low reliability
• Evaluation confidence: 72%
```

**Never hidden.** Decision-makers must see uncertainty.

## Lifecycle Summary

```
1. BREACH signal triggers policy evaluation
         │
         ▼
2. Policy evaluation FAILS
         │
         ▼
3. Exception RAISED (if not duplicate)
         │
         ▼
4. Human reviews in ONE-SCREEN UI
   - Sees context, options, uncertainty
   - Options are SYMMETRIC (no ranking)
         │
         ▼
5. Human selects option + enters RATIONALE
         │
         ▼
6. Decision COMMITTED (immutable)
         │
         ▼
7. Exception marked RESOLVED
         │
         ▼
8. Evidence Pack GENERATED (async)
   - Complete audit bundle
   - Content hash for integrity
         │
         ▼
9. Narrative Memo DRAFTED (optional)
   - Gemini grounds to evidence
   - No unsupported claims
```

## Files

- **Exception Model:** `core/models/exception.py`
- **Decision Model:** `core/models/decision.py`
- **Decision Recorder:** `core/services/decision_recorder.py`
- **Evidence Generator:** `core/services/evidence_generator.py`
- **Option Templates:** `packs/{pack}/option_templates.py`
- **Decision UI:** `ui/app/exceptions/[id]/page.tsx`
- **NarrativeAgent:** `coprocessor/agents/narrative_agent.py`
