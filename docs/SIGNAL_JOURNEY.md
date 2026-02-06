# Signal Journey: BREACH vs OBSERVATION

This document explains how signals flow through the Governance OS canonicalization layer and become either **BREACH** (triggers exception) or **OBSERVATION** (gated for review).

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         SIGNAL INGESTION FLOW                                 │
└──────────────────────────────────────────────────────────────────────────────┘

  Document/Email/API
        │
        ▼
┌──────────────────┐
│   IntakeAgent    │  Gemini extracts candidate signals from unstructured text
│   (LLM Layer)    │  with confidence scores + source spans
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Canonicalizer   │  DETERMINISTIC layer - no LLM, pure rules
│   (Pure Rules)   │  Same inputs → Same outputs ALWAYS
└────────┬─────────┘
         │
         ├──────────────────────────────────┐
         ▼                                  ▼
   ┌───────────┐                      ┌──────────────┐
   │  BREACH   │                      │ OBSERVATION  │
   └───────────┘                      └──────────────┘
   Triggers Exception                 Gated for Review
   (Human must decide)                (Missing evidence)
```

## Key Principle

**The LLM extracts facts. The Canonicalizer decides what those facts mean in governance terms.**

This separation:
- Absorbs model variance (different LLMs produce same canonical output)
- Ensures cross-model stability
- Makes the system deterministic and auditable

## Two Categories of Signals

### 1. THRESHOLD Category (can become BREACH)

Numeric violations where measured value crosses a limit.

**To become BREACH, must have:**
- All required fields present (threshold, measured value, subject)
- Pass all gates (lookthrough, definition lock, authorized threshold)

**Examples:**

| Signal Type | Required for BREACH | What happens if missing? |
|-------------|---------------------|-------------------------|
| `position_limit_breach` | `asset`, `current_position`, `limit` | → OBSERVATION |
| `covenant_breach` | `covenant_name`, `actual_ratio`, `required_ratio` | → OBSERVATION |
| `liquidity_threshold_breach` | `entity`, `current_ratio`, `threshold` | → OBSERVATION |

### 2. EVENT Category (always OBSERVATION)

Informational signals that don't represent numeric breaches.

**Always becomes OBSERVATION** - they're important but don't trigger policy violations:
- `counterparty_credit_downgrade`
- `settlement_failure`
- `debt_maturity_approaching`
- `interest_rate_reset`
- `bank_account_anomaly`

## Decision Tree

```
Signal arrives at Canonicalizer
        │
        ▼
    Is signal_type in constraints.json?
        │
        ├── NO → DROPPED (unknown signal type)
        │
        └── YES → Check category
                    │
                    ├── category == "event"
                    │       │
                    │       └── Always → OBSERVATION
                    │
                    └── category == "threshold"
                            │
                            ▼
                    Has all required_for_breach fields?
                            │
                            ├── NO → OBSERVATION (downgraded)
                            │        Flag: INCOMPLETE_THRESHOLD,
                            │              INCOMPLETE_MEASURED, etc.
                            │
                            └── YES → Check gates
                                        │
                                        ├── requires_lookthrough?
                                        │   └── Missing? → OBSERVATION
                                        │
                                        ├── requires_definition_lock?
                                        │   └── Missing? → OBSERVATION
                                        │
                                        ├── requires_authorized_threshold?
                                        │   └── Missing? → OBSERVATION
                                        │
                                        └── All gates pass → BREACH
```

## Concrete Example: Position Limit

**Constraint definition** (`packs/treasury/constraints.json`):
```json
"position_limit_breach": {
  "category": "threshold",
  "required_for_breach": ["asset", "current_position", "limit"],
  "required_for_observation": ["asset"]
}
```

### Scenario A: Complete Signal → BREACH
```json
{
  "signal_type": "position_limit_breach",
  "payload": {
    "asset": "EUR/USD",
    "current_position": 15000000,
    "limit": 10000000
  }
}
```
**Result:** `canonical_status = "breach"` → Triggers Exception → Human decides

### Scenario B: Incomplete Signal → OBSERVATION
```json
{
  "signal_type": "position_limit_breach",
  "payload": {
    "asset": "EUR/USD",
    "current_position": 15000000
    // Missing: "limit"
  }
}
```
**Result:** `canonical_status = "observation"` with flag `INCOMPLETE_THRESHOLD`
- Goes to approval queue but flagged as needing verification
- Won't trigger policy exception until complete

## Gates

Gates are additional requirements beyond field completeness.

### Definition Lock Gate

**Used by:** `covenant_breach`

```json
"covenant_breach": {
  "category": "threshold",
  "requires_definition_lock": true
}
```

If `definition_disputed: true` in payload → OBSERVATION

**Why?** Parties may disagree on how to calculate the covenant ratio. Can't declare a breach if the definition itself is contested.

### Authorized Threshold Gate

**Used by:** `fx_exposure_breach`

```json
"fx_exposure_breach": {
  "category": "threshold",
  "requires_authorized_threshold": true
}
```

If `evidence_type` isn't from `{term_sheet, fee_schedule, contract, mandate_document, loan_agreement}` → OBSERVATION

**Why?** The threshold limit must come from an authoritative source (contract, term sheet), not just an email or verbal communication.

### Lookthrough Gate

For signals requiring consolidated position data across multiple entities.

If `lookthrough_available: false` in payload → OBSERVATION

**Why?** Can't determine if limit is breached without seeing the full consolidated position.

## Flags

Canonical signals carry flags explaining their status:

| Flag | Meaning |
|------|---------|
| `COMPLETE` | All breach fields present |
| `INCOMPLETE_THRESHOLD` | Missing threshold value |
| `INCOMPLETE_MEASURED` | Missing measured value |
| `INCOMPLETE_SUBJECT` | Missing subject identifier |
| `LOOKTHROUGH_MISSING` | Lookthrough required but not available |
| `DEFINITION_LOCK_MISSING` | Definition dispute detected |
| `AUTHORIZED_THRESHOLD_MISSING` | No authorized threshold evidence |
| `DOWNGRADED` | Was threshold candidate, became observation |
| `LOW_CONFIDENCE` | Extraction confidence < 0.7 |
| `EVENT_CATEGORY` | Signal is event category (always observation) |

## UI Display

In the Signals page:
- **BREACH** (red badge) - Complete, triggered exception
- **OBSERVATION** (amber badge) - Gated, missing evidence
- **Uncategorized** - Legacy signals without canonical_status

## Files

- **Canonicalizer:** `core/domain/canonicalizer.py`
- **Signal Model:** `core/models/signal.py`
- **Constraint Registry:** `packs/{pack}/constraints.json`
- **Signal Types:** `packs/{pack}/signal_types.py`
