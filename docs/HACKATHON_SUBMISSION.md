# Gemini 3 Hackathon Submission

## Project Name
Decision Kernel

## Tagline
Deterministic Policy Engine with Transparent AI

## Description (~200 words)

Decision Kernel is a policy-driven coordination layer for high-stakes finance (Treasury & Wealth Management). It uses a **deterministic kernel** for policy evaluation while leveraging **Gemini 3** as an auditable AI coprocessor.

**Gemini 3 Features Central to the Application:**

**1. Context Caching (50-60% Cost Reduction)**
Agent prompts and domain vocabularies are cached using Gemini's caching API, with automatic invalidation when policies change. Gemini 2.5+ charges [90% less for cached input tokens](https://ai.google.dev/gemini-api/docs/pricing). Our system prompts + vocabularies are ~4,500 tokens per pack (72% of input), making the overall input cost reduction ~65%. Conservatively: 50-60% at enterprise scale.

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
- **Measured results**: On golden test documents, 14 breach-category signals across two packs. After canonicalization: 5 confirmed breaches, 9 blocked. **Two-thirds false breach prevention** with zero signal loss—every item is tracked, just honestly labeled. Reproducible via `make evals`.

This is the core safety claim: the LLM never decides severity. It finds things. A replayable, testable, deterministic function decides what they mean. Same inputs, same outputs. No randomness. Full audit trail.

**The Result:** AI that extracts, but never decides. Transparent reasoning. Deterministic validation. Two-thirds false alarm prevention—with zero missed signals. Verify it: `make evals`.

## Links

- **GitHub Repository**: https://github.com/Silveroboros-dev/Governance-OS
- **Demo Video**: [TODO: Add YouTube/Loom link]
- **Live Demo**: https://governance-os.web.app (UI) · https://govos-api-1064412167254.europe-west4.run.app/docs (API)
- **Try it yourself (MCP)**: Connect any MCP client to `https://govos-mcp-1064412167254.europe-west4.run.app/mcp` and query the governance kernel directly — ask about open exceptions, look up policies, pull evidence packs. No custom integration needed.

## Hackathon Tracks

- Enterprise AI
- Developer Tools

## Team

- [Your name]

## Built With

- Gemini 3 (Flash + Thinking Mode, Context Caching, JSON Mode, Gemini-as-Judge)
- Python / FastAPI / SQLAlchemy / Alembic / Pydantic
- Next.js / React / Tailwind CSS
- PostgreSQL
- MCP (Model Context Protocol)
- Google Cloud Run / Cloud SQL / Firebase App Hosting
- Docker
- Claude Code (vibe coding / development)

## Key Demos

```bash
# Safety check demo (shows hallucination blocking)
make demo-safety-auto

# Thinking mode demo (shows reasoning chain)
make demo-thinking-auto

# Run evaluation suite
make evals
```

## Project Story

### Inspiration

I spent years in treasury and wealth management before moving to technology. I know what it's like to review a 60-page weekly pack under time pressure — most of the "breaches" turn out to be data quality issues or definitional disputes, not real violations. But you can't ignore them because the one you skip might be real. Early experiments with Gemini 3 showed the frontier had moved — what wasn't feasible before suddenly was. I picked a hard problem I know from the inside.

### What it does

Gemini reads financial documents and extracts candidate signals. A deterministic kernel — no AI, no randomness — validates every one before it reaches a human. Two-thirds of false alarms are filtered out. The rest arrive with full context: which policy applied, what evidence supports it, and symmetric options with no recommendation. The human decides. An immutable evidence pack is generated automatically.

### How we built it

Two layers, strict separation. Gemini handles extraction (Thinking Mode for audit transparency, Context Caching for cost, JSON Mode for structured output). The kernel handles everything else: policy evaluation, completeness gating, deduplication, severity assignment, evidence generation. The Canonicalizer sits between them — a pure function that enforces category semantics, lookthrough requirements, and definition locks. 546 tests and a reproducible eval suite (`make evals`) verify the boundary holds.

### Challenges we ran into

The biggest fight was with myself. I've studied agentic workflows for two years and Gemini 3's thinking capability made multi-agent orchestration tempting. But I resisted it. Policy evaluation doesn't need non-deterministic behavior — adding agents would have made the system impressive to demo and impossible to audit. The same logic applied to the canonicalizer: I almost built it as an agent, but the job is definitional — remove duplicates, check completeness, enforce gates. That's a pure function, not a conversation.

The practical challenge was keeping two Dockerfiles, three deployment targets (Cloud Run, Cloud SQL, Firebase), and a growing test suite in sync as a solo developer.

### Accomplishments that we're proud of

The two-thirds false breach prevention rate is reproducible from a fresh clone with zero API keys — `make evals` proves it every time. The MCP server lets any AI agent query the governance kernel through a standard protocol — judges can connect and try it themselves. And the system never recommends: options are symmetric, the UI doesn't nudge, and the LLM is never the source of truth for severity or escalation.

### What we learned

I'd studied Firebase and GCP but didn't expect to use them in production any time soon. Vibe coding changed that — I went from reading docs to a deployed system on Cloud Run, Cloud SQL, and Firebase App Hosting in days, not months. The MCP protocol was new to me. Building a server that any AI agent can connect to — vendor-agnostic, auditable, read-only by default — turned out to be the cleanest architectural boundary in the project.

### What's next for Decision Kernel

The system makes the cost of bad policy visible and immediate — weak policies mean more noise, precise policies mean silence on what doesn't matter. I believe executives will realize that managing through better policies has far more ROI than fighting chaos daily. Next steps: policy authoring assistance (Gemini drafts, humans approve), replay harness for policy tuning against historical data, and expanding beyond treasury and wealth to any domain where high-stakes decisions need audit-grade evidence.
