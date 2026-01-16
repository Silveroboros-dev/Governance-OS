# Sprint 3 Plan: Full Agentic Coprocessor

**Status:** Planning
**Theme:** MCP Write Tools + IntakeAgent + Tracing + Expanded Evals
**Builds On:** Sprint 2 (MCP read-only, NarrativeAgent v0, Evals v0)

---

## Executive Summary

Sprint 3 completes the AI coprocessor layer by adding **gated write operations**, an **IntakeAgent** for unstructured signal extraction, a **tracing viewer** for agent observability, and **expanded evals** to ensure faithfulness at scale.

**Core Principle:** LLMs remain coprocessors, never sources of truth. All writes go through approval gates with full audit trails.

---

## Deliverables Overview

| Track | Deliverable | Description |
|-------|-------------|-------------|
| A | MCP Write Tools | Gated write operations with approval flows |
| B | IntakeAgent | Extract candidate signals from unstructured docs |
| C | PolicyDraftAgent | Generate draft policy versions from descriptions |
| D | Tracing Viewer | UI for agent execution observability |
| E | Expanded Evals | Extraction accuracy + kernel regression tests |

---

## Track A: MCP Write Tools

### Goal
Add write capabilities to MCP server with explicit approval gates and audit events.

### New Tools

| Tool | Description | Approval Required |
|------|-------------|-------------------|
| `propose_signal` | Create candidate signal for human review | Yes - Signal Review |
| `propose_policy_draft` | Create draft policy version | Yes - Policy Approval |
| `add_exception_context` | Enrich exception with additional context | No (additive only) |
| `propose_decision` | Suggest decision with rationale (NO RECOMMENDATION) | Yes - Human Decision |
| `dismiss_exception` | Mark exception as dismissed with reason | Yes - Dismiss Approval |

### Safety Architecture

```
Agent Request → MCP Tool → Approval Queue → Human Review → Kernel Write → Audit Event
```

**Key Invariants:**
- All writes create `pending_approval` records
- No direct database mutations from agents
- Every approval/rejection logged to `AuditEvent`
- Approval UI shows full agent reasoning

### Database Schema Additions

```sql
-- Approval queue for agent-proposed actions
CREATE TABLE approval_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type VARCHAR(50) NOT NULL,  -- 'signal', 'policy_draft', 'decision', 'dismiss'
    payload JSONB NOT NULL,
    proposed_by VARCHAR(100) NOT NULL,  -- agent identifier
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    result_id UUID  -- ID of created entity if approved
);

-- Agent execution traces
CREATE TABLE agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,  -- 'intake', 'narrative', 'policy_draft'
    session_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,  -- 'running', 'completed', 'failed'
    input_summary JSONB,
    output_summary JSONB,
    tool_calls JSONB[],  -- Array of {tool, args, result, duration_ms}
    error_message TEXT
);
```

### API Endpoints

```
POST /api/v1/approvals/{id}/approve
POST /api/v1/approvals/{id}/reject
GET  /api/v1/approvals?status=pending&action_type=signal
GET  /api/v1/approvals/{id}
```

### Files to Create

```
/mcp_server/
  tools/
    write_tools.py         # New write tool implementations
  approval_gate.py         # Approval queue logic

/core/
  models/approval.py       # ApprovalQueue model
  models/trace.py          # AgentTrace model
  api/routers/approvals.py # Approval API endpoints
  schemas/approval.py      # Pydantic schemas
```

---

## Track B: IntakeAgent

### Goal
Extract candidate structured signals from unstructured documents (PDFs, emails, reports) with provenance tracking.

### Architecture

```
Document → IntakeAgent → Candidate Signals → Approval Queue → Human Review → Signal Ingestion
```

### Agent Specification

**Input:**
- Document content (text extracted from PDF/email/report)
- Document metadata (source, received_at, sender)
- Target pack (treasury/wealth) for signal type vocabulary

**Output:**
```python
class CandidateSignal(BaseModel):
    signal_type: str  # Must match pack vocabulary
    payload: Dict[str, Any]
    confidence: float  # 0.0-1.0
    source_spans: List[SourceSpan]  # Where in document this came from
    extraction_notes: str  # Agent's reasoning
```

**Key Constraints:**
- Must output pack-valid signal types only
- Every field must have source_span reference
- Confidence < 0.7 requires human verification flag
- Never infer values not explicitly stated

### Source Span Schema

```python
class SourceSpan(BaseModel):
    start_char: int
    end_char: int
    text: str  # Exact quoted text
    page: Optional[int]  # For PDFs
```

### Files to Create

```
/coprocessor/
  agents/
    intake_agent.py        # Main intake agent
  schemas/
    extraction.py          # CandidateSignal, SourceSpan
  prompts/
    intake_system.txt      # System prompt for extraction
    intake_treasury.txt    # Treasury-specific examples
    intake_wealth.txt      # Wealth-specific examples
```

### MCP Integration

```python
@mcp.tool()
def extract_signals_from_document(
    content: str,
    pack: str,
    document_source: str,
    document_metadata: Optional[Dict] = None
) -> List[Dict]:
    """
    Extract candidate signals from unstructured document.

    Returns candidate signals that require human approval before ingestion.
    Each candidate includes confidence score and source spans for verification.
    """
```

---

## Track C: PolicyDraftAgent

### Goal
Generate draft policy versions from natural language descriptions, always requiring human approval.

### Architecture

```
Policy Description → PolicyDraftAgent → Draft PolicyVersion → Approval Queue → Human Review → Policy Publish
```

### Agent Specification

**Input:**
- Natural language policy description
- Target pack (treasury/wealth)
- Reference to existing policy (if updating)

**Output:**
```python
class PolicyDraft(BaseModel):
    name: str
    description: str
    rule_definition: Dict[str, Any]  # Must match evaluation_rules schema
    signal_types_referenced: List[str]  # Signals this policy evaluates
    change_reason: str
    draft_notes: str  # Agent's reasoning about rule construction
```

**Key Constraints:**
- Rule definitions must be deterministically evaluatable
- Only use signal types from target pack vocabulary
- Never auto-approve - all drafts go to approval queue
- Include test scenarios showing expected behavior

### Files to Create

```
/coprocessor/
  agents/
    policy_draft_agent.py  # Policy drafting agent
  schemas/
    policy_draft.py        # PolicyDraft schema
  prompts/
    policy_draft_system.txt
```

---

## Track D: Tracing Viewer

### Goal
Provide UI observability into agent execution for debugging and audit.

### UI Components

**Trace List Page (`/traces`):**
- List all agent executions
- Filter by agent type, status, date range
- Show duration, tool call count, outcome

**Trace Detail Page (`/traces/[id]`):**
- Timeline of tool calls with expand/collapse
- Input/output for each tool call
- Error details if failed
- Link to resulting approvals/entities

### Trace Timeline Component

```
┌─────────────────────────────────────────────────────────────┐
│ IntakeAgent - session_abc123                                │
│ Started: 2026-01-14T10:00:00Z  Duration: 3.2s  Status: ✓    │
├─────────────────────────────────────────────────────────────┤
│ ○ get_policies (treasury)                           120ms   │
│   └─ Returned 6 policies                                    │
│ ○ extract_signals_from_document                     2800ms  │
│   └─ Extracted 3 candidate signals                          │
│ ○ propose_signal (position_limit_breach)            180ms   │
│   └─ Created approval_queue entry: apq_xyz789               │
│ ○ propose_signal (market_volatility_spike)          150ms   │
│   └─ Created approval_queue entry: apq_xyz790               │
└─────────────────────────────────────────────────────────────┘
```

### Files to Create

```
/ui/
  app/
    traces/
      page.tsx              # Trace list page
      [id]/
        page.tsx            # Trace detail page
  components/
    traces/
      TraceList.tsx
      TraceTimeline.tsx
      ToolCallDetail.tsx
```

### API Endpoints

```
GET  /api/v1/traces?agent_type=intake&status=completed&limit=50
GET  /api/v1/traces/{id}
GET  /api/v1/traces/{id}/tool-calls
```

---

## Track E: Expanded Evals

### Goal
Add extraction accuracy evals and kernel regression tests to CI.

### New Eval Suites

**1. Extraction Accuracy (`/evals/extraction/`):**
- Golden set of documents with expected signals
- Measure precision/recall of signal extraction
- Flag confidence calibration issues

```python
class ExtractionEval:
    def evaluate(self, agent: IntakeAgent, document: str, expected: List[Signal]) -> EvalResult:
        extracted = agent.extract(document)
        return EvalResult(
            precision=self.calc_precision(extracted, expected),
            recall=self.calc_recall(extracted, expected),
            confidence_calibration=self.check_calibration(extracted, expected),
        )
```

**2. Kernel Regression (`/evals/regression/`):**
- Replay historical decisions
- Verify deterministic outputs match
- Detect policy drift

```python
class RegressionEval:
    def evaluate(self, historical_pack: str) -> EvalResult:
        results = replay_harness.run(historical_pack)
        return EvalResult(
            matches=results.matching_count,
            mismatches=results.mismatch_details,
            drift_detected=len(results.mismatch_details) > 0,
        )
```

**3. Policy Draft Validity (`/evals/policy_draft/`):**
- Verify generated rules are syntactically valid
- Check all referenced signal types exist
- Test rule evaluation doesn't throw

### CI Integration

```yaml
# .github/workflows/evals.yml
evals:
  runs-on: ubuntu-latest
  steps:
    - name: Run extraction evals
      run: python -m evals.runner --suite extraction --threshold 0.85

    - name: Run kernel regression
      run: python -m evals.runner --suite regression --fail-on-drift

    - name: Run hallucination checks
      run: python -m evals.runner --suite hallucination --zero-tolerance
```

### Files to Create

```
/evals/
  extraction/
    __init__.py
    evaluator.py
    datasets/
      treasury_docs.json
      wealth_docs.json
  regression/
    __init__.py
    evaluator.py
  policy_draft/
    __init__.py
    evaluator.py
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Database migrations for `approval_queue` and `agent_traces`
- [ ] Approval queue service and API endpoints
- [ ] Basic approval UI (list + approve/reject)
- [ ] Agent trace logging infrastructure

### Phase 2: Write Tools (Week 2)
- [ ] MCP `propose_signal` tool with approval gate
- [ ] MCP `propose_policy_draft` tool
- [ ] MCP `dismiss_exception` tool
- [ ] Approval UI enhancements (show agent reasoning)

### Phase 3: IntakeAgent (Week 3)
- [ ] IntakeAgent implementation
- [ ] Source span extraction
- [ ] Pack-specific prompt tuning
- [ ] Integration with approval queue

### Phase 4: PolicyDraftAgent (Week 3-4)
- [ ] PolicyDraftAgent implementation
- [ ] Rule definition generation
- [ ] Test scenario generation
- [ ] Approval workflow integration

### Phase 5: Tracing & Evals (Week 4)
- [ ] Trace viewer UI
- [ ] Extraction accuracy evals
- [ ] Kernel regression evals
- [ ] CI integration

---

## Safety Checklist

Before marking Sprint 3 complete, verify:

- [ ] **No direct writes:** All agent actions go through approval queue
- [ ] **Audit trail:** Every approval/rejection creates AuditEvent
- [ ] **No recommendations:** PolicyDraftAgent never suggests "best" options
- [ ] **Grounding enforced:** IntakeAgent outputs have source spans
- [ ] **Confidence visible:** Low-confidence extractions flagged in UI
- [ ] **Evals gating CI:** Hallucination checks block merge on failure
- [ ] **Determinism preserved:** Kernel regression tests pass

---

## Dependencies

### Python Packages
```
anthropic>=0.18.0  # Already in requirements
mcp>=0.1.0         # For MCP server
pypdf>=3.0.0       # PDF text extraction
```

### Environment Variables
```
ANTHROPIC_API_KEY  # Required for agents
MCP_SERVER_PORT    # Default 3001
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Extraction precision | > 85% |
| Extraction recall | > 80% |
| Confidence calibration | ±10% |
| Kernel regression | 100% match |
| Hallucination rate | 0% |
| Approval latency | < 500ms |

---

## Open Questions

1. **Batch approvals:** Should we allow approving multiple signals at once?
2. **Auto-approval threshold:** Should high-confidence extractions (>0.95) auto-approve?
3. **Policy draft testing:** How many test scenarios should each draft include?
4. **Trace retention:** How long to keep agent traces? (Suggest: 90 days)

---

## Related Documents

- [SPRINT2_PROGRESS.md](./SPRINT2_PROGRESS.md) - What we built
- [CLAUDE.md](./CLAUDE.md) - Architecture principles
- [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md) - Current state

---

*Sprint 3 transforms Governance OS from a decision-support system into a full agentic platform while maintaining the non-negotiable safety boundaries around determinism, immutability, and human-in-the-loop approvals.*
