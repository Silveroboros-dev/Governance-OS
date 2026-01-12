# Contributing to Governance OS

Thanks for contributing. This project is intentionally strict: it is a **governance system**, not a productivity app or copilot.

If you propose changes that dilute accountability, hide uncertainty, or introduce nondeterminism into the core loop, they will be rejected.

---

## What we’re building (short)

Governance OS converts signals into deterministic policy evaluations, raises exceptions when human judgment is required, records decisions immutably, and generates audit-grade evidence packs.

**Core loop:** Signal → Policy Evaluation → Exception → Decision → Evidence/Outcome

---

## Non-negotiable design & engineering doctrine

### 1) Deterministic kernel
The following must remain **deterministic**, testable, and replayable:
- signal ingestion validation + canonicalization
- policy evaluation
- exception generation + dedupe
- decision logging (immutability)
- evidence pack generation

If the system cannot be replayed against the same dataset with identical results, it’s a regression.

### 2) No recommendations in the decision layer
The decision surface must not:
- rank options
- highlight a default
- label anything “recommended”
- nudge choices via visual emphasis

The UI must present **symmetric trade-offs**. The human owns the decision.

### 3) One-screen commitment surface
The primary exception/decision experience is one screen:
- no scrolling
- no rabbit-hole drilldowns as default
- deep exploration belongs in secondary surfaces after commitment

### 4) Uncertainty is first-class
Do not “clean up” uncertainty. Confidence and unknowns must remain visible and explicit.

### 5) Memory is not logging
We record decisions and evidence to:
- defend decisions (audit/board/regulator)
- learn and tune policies over time

Not to generate analytics dashboards for their own sake.

---

## Where LLMs/agents are allowed (and where they are not)

LLMs may be used ONLY as an optional coprocessor for:
- extracting candidate structured signals from unstructured inputs (with provenance + confidence)
- drafting narratives from existing evidence graph (never source of truth)
- policy authoring assistance (human-approved)

LLMs must NOT be used for:
- policy evaluation
- severity/escalation decisions
- evidence pack “truth”
- silent automation that changes state without explicit boundaries

---

## How to propose changes

### For features
Open an issue with:
- the user scenario and expected outcome
- which kernel objects are affected (Policy/Signal/Evaluation/Exception/Decision/Evidence)
- determinism impact (replayability)
- audit impact (traceability)

### For UI changes
Include screenshots or a short screencap and explicitly state:
- does this change affect symmetry?
- does it add “recommendation” or implied default?
- does it add depth to the commitment surface?

---

## Development setup

### Run local
```bash
docker compose up --build
```
## Tests

Backend:
```bash
pytest
```
## Frontend:
```bash
npm test
```
## Pull request checklist (required)

 Includes tests or clear manual test plan

 Preserves determinism for affected parts (or documents why it doesn’t apply)

 Does not introduce recommendations or defaults into decision surface

 Does not add scrolling or drilldowns to the commitment screen

 Adds/updates migrations if schema changed

 Updates README/docs if behavior or APIs changed
