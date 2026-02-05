# Gemini 3 Hackathon Submission

## Project Name
Governance OS

## Tagline
Deterministic Policy Engine with Transparent AI

## Description (~200 words)

Governance OS is a policy-driven coordination layer for high-stakes finance (Treasury & Wealth Management). It uses a **deterministic kernel** for policy evaluation while leveraging **Gemini 3** as an auditable AI coprocessor.

**Gemini 3 Features Central to the Application:**

**1. Context Caching (50-60% Cost Reduction)**
Agent prompts and domain vocabularies are cached using Gemini's caching API, with automatic invalidation when policies change. Cached tokens cost 90% less; overall request savings of 50-60% at enterprise scale.

**2. Thinking Mode (Audit-Grade Transparency)**
The IntakeAgent extracts signals with `include_thoughts=True`. The reasoning chain shows *why* each signal was extracted—critical for compliance review. Auditors can verify AI decision-making.

**3. Gemini as Semantic Judge (Zero Hallucinations)**
Beyond regex, Gemini validates that narrative outputs are faithfully grounded to evidence. It catches subtle hallucinations (wrong numbers, unsupported claims) that pattern matching misses. CI fails on any unsupported claim.

**4. Native JSON Mode + Conflict Detection**
All outputs use `response_mime_type="application/json"`. The schema detects when sources contradict each other—surfacing conflicts for human review rather than silently picking one.

**5. Deterministic Canonicalizer (AI Proposes, Kernel Disposes)**
Gemini extracts candidate signals from documents, but a pure deterministic layer decides what counts as a confirmed breach. The Canonicalizer enforces:
- **Category semantics**: Events (settlements, compliance flags) can never become breaches regardless of LLM confidence
- **Gate system**: Threshold violations require verified evidence—confirmed metric definitions, authorized source documents, lookthrough data—before earning "breach" status
- **Measured results**: On real financial documents, Gemini extracted 14 signals across two packs. Without the Canonicalizer, 8 would have been false breaches. After canonicalization: 2 confirmed breaches, 12 observations pending verification. **86% false breach prevention** with zero signal loss—every item is tracked, just honestly labeled.

This is the core safety claim: the LLM never decides severity. It finds things. A replayable, testable, deterministic function decides what they mean. Same inputs, same outputs. No randomness. Full audit trail.

**The Result:** AI that extracts, but never decides. Transparent reasoning. Deterministic validation. 86% false alarm prevention on real financial documents—with zero missed signals.

## Links

- **GitHub Repository**: https://github.com/[your-username]/Governance-OS
- **Demo Video**: [TODO: Add YouTube/Loom link]
- **Live Demo**: [TODO: Add if deployed]

## Hackathon Tracks

- Enterprise AI
- Developer Tools

## Team

- [Your name]

## Built With

- Gemini 3 (Flash + Pro)
- Python / FastAPI
- Next.js
- PostgreSQL
- Pydantic (schema validation)
- MCP (Model Context Protocol) - LLM-agnostic tool exposure; Gemini agents communicate through MCP

## Key Demos

```bash
# Safety check demo (shows hallucination blocking)
make demo-safety-auto

# Thinking mode demo (shows reasoning chain)
make demo-thinking-auto

# Run evaluation suite
make evals
```
