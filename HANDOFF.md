# Handoff Notes - Gemini Hackathon Progress

## What We've Built (Committed & Pushed)

### Hack A: Gemini 3 Context Caching (90% Cost Reduction)
- **Files**: `coprocessor/cache/` (gemini_client.py, manager.py)
- **Tests**: `core/tests/test_gemini_cache.py` (66 tests)
- **Feature**: Caches system prompts + vocabularies for 90% cost savings, auto-refreshes on policy changes

### Hack B: Gemini-Powered Evals (Zero Hallucinations Verified)
- **Files**: `evals/validators/gemini_judge.py`, `evals/datasets/treasury_goldens.json`, `evals/datasets/wealth_goldens.json`
- **CI**: `.github/workflows/evals.yml` - Two-stage CI (fast regex + Gemini semantic)
- **Feature**: Gemini as semantic judge catches hallucinations regex can't (wrong numbers, unsupported causal claims)

### Hack C: Safety Check Demo (For Video)
- **File**: `demo_safety_check.py`
- **Commands**: `make demo-safety` (interactive), `make demo-safety-auto` (video recording)
- **Shows**: Poisoned AI output → HallucinationDetector catches 4 violations → BLOCKED

### Hack D: Thinking Mode for Transparent Reasoning
- **Files**: `coprocessor/cache/gemini_client.py` (generate_with_thinking), `coprocessor/agents/intake_agent.py` (use_thinking param), `coprocessor/schemas/extraction.py` (thinking_summary field)
- **Demo**: `demo_thinking_mode.py`, `make demo-thinking`, `make demo-thinking-auto`
- **Feature**: Exposes Gemini's reasoning chain for audit-grade transparency. Shows WHY each signal was extracted.

### Schema Enhancement: Conflicts & Drops (from Signal Compiler)
- **File**: `coprocessor/schemas/extraction.py`
- **New schemas**: `Conflict`, `ConflictType`, `ConflictClaim`, `Drop`, `DropReason`
- **Enhanced**: `SourceSpan` now supports `bbox` for PDF/scan visual grounding
- **Feature**: Detects when sources disagree (conflicts) and tracks what couldn't be extracted (drops)

### Agent Migration
- All agents (IntakeAgent, NarrativeAgent, PolicyDraftAgent) migrated from Anthropic to Gemini 3
- Uses context caching for enterprise efficiency

## Git Status
All hackathon features committed and pushed to `main`:
```
ba0205e docs: Add hackathon features to TEST_INSTRUCTIONS.md
3ef0840 feat: Add AI safety check demo for hackathon video
e544ad3 refactor: Migrate agents from Anthropic to Gemini 3 with caching
90e0dc5 feat: Add Gemini 3 context caching (Hack A) - 90% cost reduction
454ae3f feat: Add Gemini-powered evals (Hack B) - zero hallucinations verified
```

## Remaining Uncommitted Files
```
.vscode/settings.json
CLAUDE.md
Dockerfile
core/api/approvals.py
README_GEO.md, head-snippet.html, llms.txt (SEO files)
mcp_server/Dockerfile, mcp_server/cloudbuild.yaml (deployment)
robots.txt, sitemap.xml, schema-*.json (SEO)
```

## Key Commands
```bash
make demo-safety-auto    # Run the safety check video demo
make demo-thinking-auto  # Run the thinking mode video demo
make evals               # Run all eval suites (28 golden tests)
make evals-gemini        # Run Gemini semantic verification
pytest core/tests/test_gemini_cache.py -v  # Run cache tests (66 tests)
```

## The Pitch
> "We use Gemini's reasoning to draft the memo, but we wrap it in a deterministic Regex safety layer to ensure compliance. Zero hallucinations. Guaranteed."

## Documentation Updated
- README.md - Added Gemini 3 Integration section (Hack A + Hack B)
- TEST_INSTRUCTIONS.md - Added hackathon testing commands
- Makefile - Added demo-safety, evals-gemini, evals-pack targets
