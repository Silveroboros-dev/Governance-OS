# Governance OS — Clean Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            GOVERNANCE OS — CLEAN ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────────────┘

  INBOUND ADAPTERS                    CORE                           OUTBOUND ADAPTERS
  ─────────────────                   ────                           ─────────────────
  ┌───────────────┐                                                  ┌───────────────┐
  │  UI (Next.js) │──┐                                           ┌──│  PostgreSQL   │
  ├───────────────┤  │                                           │  ├───────────────┤
  │  API (FastAPI)│──┤                                           │  │  Gemini API   │
  ├───────────────┤  │                                           │  │  (extraction) │
  │  MCP Server   │──┤         ┌─────────────────────────┐       │  └───────────────┘
  ├───────────────┤  │         │      APPLICATION        │       │         ▲
  │  CLI / Evals  │──┼────────▶│      ───────────        │◀──────┼─────────┘
  └───────────────┘            │  IntakeAgent            │       │   (via ports)
                               │  ReplayHarness          │       │
                               │  ApprovalWorkflow       │───────┘
                               └───────────┬─────────────┘
                                           │
                                           ▼
                               ┌─────────────────────────┐
                               │      DOMAIN CORE        │
                               │      ───────────        │
                               │  • Canonicalizer        │
                               │  • Policy Evaluator     │
                               │  • Exception Engine     │
                               │  • Evidence Generator   │
                               │                         │
                               │  ✓ Pure functions       │
                               │  ✓ No I/O, no LLM calls │
                               │  ✓ Zero dependencies    │
                               └─────────────────────────┘

  ════════════════════════════════════════════════════════════════════════════════════
  DEPENDENCY RULE: Outer layers depend inward only. Domain Core has ZERO dependencies.
  ════════════════════════════════════════════════════════════════════════════════════

  DATA FLOW:
  ┌────────────────────────────────────────────────────────────────────────────────┐
  │  Gemini extracts 14 candidates → Kernel outputs 4 confirmed breaches;         │
  │  remaining candidates are downgraded/merged/dropped → Only breaches escalate  │
  └────────────────────────────────────────────────────────────────────────────────┘

  CRITICAL INVARIANT: No direct Gemini → Policy Decision write path.
                      LLM output MUST pass through deterministic kernel.
```

