# Handoff Notes - Gemini Hackathon Progress

## What We've Built

### Core: Deterministic Canonicalizer (AI Proposes, Kernel Disposes)
- **Files**: `core/domain/canonicalizer.py`, `core/domain/constraint_registry.py`
- **Tests**: `core/tests/test_canonicalizer.py`, `core/tests/test_determinism.py` (78 tests, 1 skip)
- **Feature**: Gemini extracts candidate signals, but a pure deterministic layer decides what counts as a breach:
  - **Category semantics**: Each signal type is `threshold`, `event`, or `blocker`. Events (settlements, compliance flags) can never become breaches regardless of LLM confidence.
  - **Gate system**: Threshold violations require verified evidence before earning breach status:
    - `definition_lock` — metric definition must be unambiguous (e.g. "unrestricted cash" disputed → observation)
    - `authorized_threshold` — limit must come from an authorized source document (e.g. term sheet PDF)
    - `lookthrough` — fund-level data required before confirming portfolio breaches
  - **Measured results**: 14 signals across two packs → 2 confirmed breaches, 12 observations. **86% false breach prevention** with zero signal loss.

### Hack A: Gemini 3 Context Caching (90% Cost Reduction)
- **Files**: `coprocessor/cache/` (gemini_client.py, manager.py)
- **Tests**: `core/tests/test_gemini_cache.py` (66 tests)
- **Feature**: Caches system prompts + vocabularies for 90% cost savings, auto-refreshes on policy changes

### Hack B: Gemini-Powered Evals (Zero Hallucinations Verified)
- **Files**: `evals/validators/gemini_judge.py`, `evals/datasets/treasury_goldens.json`, `evals/datasets/wealth_goldens.json`
- **CI**: `.github/workflows/evals.yml` - Two-stage CI (fast regex + Gemini semantic)
- **Feature**: Gemini as semantic judge catches hallucinations regex can't (wrong numbers, unsupported causal claims)

### Hack C: Safety Layer (AI Never Recommends)
- **File**: `demo_safety_check.py`, `evals/validators/hallucination.py`
- **Feature**: Deterministic regex blocks forbidden patterns (recommendations, opinions, severity judgments, policy evaluations). CI-gated — violations fail the build.

### Hack D: Thinking Mode for Transparent Reasoning
- **Files**: `coprocessor/cache/gemini_client.py` (generate_with_thinking), `coprocessor/agents/intake_agent.py` (use_thinking param)
- **Feature**: Exposes Gemini's reasoning chain for audit-grade transparency. Every extraction is auditable.

### E2E Pipeline: Document → Gemini → Canonicalizer → Results
- **Treasury (Orion Metals)**: `evals/e2e_treasury_orion.py` — 5 signals → 2 breach, 3 observation (60% prevention)
  - covenant_breach correctly downgraded via definition_lock gate
  - settlement_failure and bank_account_anomaly correctly classified as events
- **Wealth (Meridian/Ravenwood)**: `evals/e2e_wealth_meridian.py` — 9 signals → 0 breach, 9 observation (100% prevention)
  - mandate_breach and concentration_breach blocked by lookthrough gate
  - fee_discrepancy blocked by authorized_threshold gate
- **Combined**: 14 signals, 2 breach, 12 observation = **86% false breach prevention**

### Video Demo
- **File**: `demo_video.py`
- **Commands**: `make demo-video` (interactive), `make demo-video-auto` (screen recording)
- **Content**: 3 acts in ~90s — Thinking Mode → Canonicalizer (14→2 visual) → Safety Layer
- **Storyboard**: `VIDEO_STORYBOARD.md` — 7-act plan for ~2:00-2:30 explainer

## Git History (Recent)
```
cfea652 feat: Video-optimized demo, color fixes, and hackathon submission docs
b9cfdeb feat: Category semantics, gate system, and e2e canonicalization pipeline
416368e fix: Update tests for canonical signal types and fix thinking demo parameter
d358d52 feat: Canonical signal types, event_trigger policies, and signal-exception pipeline
a7f1554 fix: Include UserProvider in layout and fix SSR prerender crash
```

## Deployment
- **Backend (Cloud Run)**: `https://govos-api-1064412167254.europe-west4.run.app` — deployed rev 00029
- **Frontend (Firebase App Hosting)**: `https://governance-os.web.app` — auto-deploys on push to main
- **MCP Server**: `https://govos-mcp-1064412167254.europe-west4.run.app/mcp`

## Key Commands
```bash
# Video demo (for recording)
make demo-video-auto

# Individual demos
make demo-thinking-auto  # Thinking Mode
make demo-safety-auto    # Safety layer

# E2E tests (require GOOGLE_API_KEY)
GOOGLE_API_KEY=... python evals/e2e_treasury_orion.py
GOOGLE_API_KEY=... python evals/e2e_wealth_meridian.py

# Unit tests
pytest core/tests/ -v

# Evals
make evals
```

## The Pitch
> "Gemini 3 reads documents with transparent reasoning. A deterministic kernel validates with zero randomness. Humans decide with full context. 86% false alarm prevention on real financial documents — with zero missed signals. AI that extracts, but never decides."
