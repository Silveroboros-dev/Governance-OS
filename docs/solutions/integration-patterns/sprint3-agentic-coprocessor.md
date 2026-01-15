# Sprint 3: Agentic Coprocessor Implementation

```yaml
title: Sprint 3 Agentic Coprocessor with Approval-Gated Writes
category: integration-patterns
tags: [sprint3, agents, mcp, approvals, tracing, evals, coprocessor, intake-agent, policy-draft-agent, timezone, postgresql]
component: ai-coprocessor-layer
severity: n/a
date_resolved: 2026-01-15
patterns_established:
  - approval_queue_pattern
  - agent_trace_logging
  - timezone_normalization
  - mcp_write_tools_with_gates
  - pack_vocabulary_validation
gotchas:
  - postgresql_timezone_aware_returns
  - python_utcnow_naive
  - sqlalchemy_datetime_column_timezone_param
metrics:
  files_created: 46
  tests_added: 115
  total_tests: 302
```

---

## Problem Statement

Sprint 3 required implementing a full agentic coprocessor layer while maintaining the safety invariants of the deterministic governance kernel:

1. **Agents must never make decisions** - only propose actions for human approval
2. **Full observability** - every agent execution must be traceable
3. **Pack vocabulary enforcement** - agents can only output valid signal types
4. **Source provenance** - every extraction must cite its source in the document

---

## Solution Architecture

### 1. Approval Queue Pattern (Gated Writes)

All agent-initiated writes go through an approval queue before affecting the deterministic kernel.

**File: `core/models/approval.py`**

```python
class ApprovalActionType(str, PyEnum):
    SIGNAL = "signal"           # IntakeAgent proposes new signal
    POLICY_DRAFT = "policy_draft"  # PolicyDraftAgent proposes policy
    DISMISS = "dismiss"         # Agent proposes dismissing exception

class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalQueue(Base):
    action_type = Column(SQLEnum(ApprovalActionType, ...))
    status = Column(SQLEnum(ApprovalStatus, ...), default=ApprovalStatus.PENDING)
    payload = Column(JSONB, nullable=False)  # What the agent wants to do
    proposed_by = Column(String(100), nullable=False)  # Which agent
    trace_id = Column(UUID, ForeignKey("agent_traces.id"))  # Link to execution
```

**Usage in MCP Tools:**

```python
# mcp_server/tools/write_tools.py
class ProposeSignalTool:
    async def execute(self, arguments: dict, context: dict) -> ToolResult:
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            status=ApprovalStatus.PENDING,  # Always pending
            payload=arguments,
            proposed_by=context.get("agent_type", "unknown"),
            trace_id=context.get("trace_id"),
        )
        db.add(approval)
        db.commit()
        return ToolResult(success=True, data={"approval_id": approval.id})
```

### 2. Agent Tracing Pattern (Observability)

Every agent execution is traced with tool calls, timing, and completion status.

**File: `core/models/trace.py`**

```python
class AgentTrace(Base):
    agent_type = Column(SQLEnum(AgentType, ...))
    session_id = Column(UUID, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(AgentTraceStatus, ...), default=AgentTraceStatus.RUNNING)
    tool_calls = Column(ARRAY(JSONB), nullable=True)  # Log of all tool invocations

    def add_tool_call(self, tool: str, args: dict, result: Any, duration_ms: int):
        call = {
            "tool": tool,
            "args": args,
            "result": result,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.tool_calls = self.tool_calls + [call]
```

### 3. Pack Vocabulary Validation

Agents can only output signal types from the pack's vocabulary.

**File: `coprocessor/schemas/extraction.py`**

```python
TREASURY_SIGNAL_TYPES = [
    "position_limit_breach",
    "counterparty_exposure_change",
    "credit_rating_change",
    # ... explicit whitelist
]

WEALTH_SIGNAL_TYPES = [
    "risk_tolerance_change",
    "beneficiary_update",
    "portfolio_drift",
    # ... explicit whitelist
]

def validate_signal_type_for_pack(signal_type: str, pack: str) -> bool:
    if pack == "treasury":
        return signal_type in TREASURY_SIGNAL_TYPES
    elif pack == "wealth":
        return signal_type in WEALTH_SIGNAL_TYPES
    return False
```

### 4. Source Span Provenance

Every extraction must cite where in the document it came from.

**File: `coprocessor/schemas/extraction.py`**

```python
class SourceSpan(BaseModel):
    start_char: int = Field(..., ge=0)
    end_char: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)  # Actual quoted text

class CandidateSignal(BaseModel):
    signal_type: str
    payload: Dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_spans: List[SourceSpan] = Field(..., min_length=1)  # Required!
```

---

## Bug Fix: Timezone-Aware vs Timezone-Naive Datetimes

### Problem

PostgreSQL `DateTime(timezone=True)` returns timezone-aware datetimes, but Python's `datetime.utcnow()` returns timezone-naive. This caused `TypeError` when calculating durations:

```
TypeError: can't subtract offset-naive and offset-aware datetimes
```

### Root Cause

- `started_at` stored in PostgreSQL as `TIMESTAMP WITH TIME ZONE`
- When retrieved, SQLAlchemy returns timezone-aware datetime
- `datetime.utcnow()` returns timezone-naive datetime
- Subtraction fails due to mismatch

### Solution

**File: `core/models/trace.py:122-149`**

```python
def complete(self, output_summary: Optional[Dict[str, Any]] = None):
    self.status = AgentTraceStatus.COMPLETED
    self.completed_at = datetime.utcnow()

    if self.started_at:
        try:
            # Handle timezone-aware/naive datetime comparison
            started = self.started_at.replace(tzinfo=None) if self.started_at.tzinfo else self.started_at
            completed = self.completed_at.replace(tzinfo=None) if hasattr(self.completed_at, 'tzinfo') and self.completed_at.tzinfo else self.completed_at
            self.total_duration_ms = int((completed - started).total_seconds() * 1000)
        except (AttributeError, TypeError):
            self.total_duration_ms = None  # Graceful degradation
```

### Prevention

```python
# Option 1: Always use timezone-aware (recommended)
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# Option 2: Strip timezone before comparison
def safe_duration(start, end):
    start = start.replace(tzinfo=None) if start.tzinfo else start
    end = end.replace(tzinfo=None) if end.tzinfo else end
    return (end - start).total_seconds()
```

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_sprint3_approvals.py` | 13 | ApprovalQueue model, approve/reject, queries |
| `test_sprint3_traces.py` | 16 | AgentTrace model, tool calls, complete/fail |
| `test_sprint3_schemas.py` | 24 | SourceSpan, CandidateSignal, ExtractionResult |
| `test_sprint3_agents.py` | 27 | IntakeAgent parsing, validation, safety |
| `test_sprint3_evals.py` | 35 | Extraction, regression, policy draft evals |
| **Total** | **115** | Full Sprint 3 coverage |

### Safety Invariant Tests

```python
class TestIntakeAgentSafetyInvariants:
    def test_only_pack_vocabulary_signal_types(self):
        """SAFETY: Agent must only output signal types from pack vocabulary."""
        assert validate_signal_type_for_pack("position_limit_breach", "treasury") is True
        assert validate_signal_type_for_pack("risk_tolerance_change", "treasury") is False

    def test_source_spans_required(self):
        """SAFETY: Every extraction must have source spans."""
        with pytest.raises(Exception):
            CandidateSignal(signal_type="test", source_spans=[])  # Fails

    def test_confidence_bounded(self):
        """SAFETY: Confidence scores must be in [0.0, 1.0]."""
        with pytest.raises(Exception):
            CandidateSignal(confidence=1.5)  # Fails
```

---

## Key Files Created

```
# Models & Schemas
core/models/approval.py          # ApprovalQueue model
core/models/trace.py             # AgentTrace model
core/schemas/approval.py         # API schemas
core/schemas/trace.py            # API schemas

# API Endpoints
core/api/approvals.py            # Approval CRUD + approve/reject
core/api/traces.py               # Trace listing + detail

# Agents
coprocessor/agents/intake_agent.py       # Signal extraction
coprocessor/agents/policy_draft_agent.py # Policy generation
coprocessor/schemas/extraction.py        # Extraction schemas
coprocessor/schemas/policy_draft.py      # Policy draft schemas

# MCP Write Tools
mcp_server/tools/write_tools.py  # propose_signal, propose_policy_draft, etc.

# Evals
evals/extraction/evaluator.py    # Precision/recall/F1
evals/regression/evaluator.py    # Kernel determinism
evals/policy_draft/evaluator.py  # Policy draft validation

# UI
ui/app/approvals/page.tsx        # Approval dashboard
ui/app/traces/page.tsx           # Trace list
ui/app/traces/[id]/page.tsx      # Trace detail

# Tests
core/tests/test_sprint3_*.py     # 115 tests
```

---

## Prevention Strategies

### 1. AI Safety Boundaries

- **All agent writes through ApprovalQueue** - never direct DB mutations
- **Pack vocabulary whitelist** - explicit enum of valid signal types
- **Source span requirement** - `min_length=1` on source_spans field
- **Confidence clamping** - `max(0.0, min(1.0, confidence))`

### 2. Timezone Handling

- **Strip timezone for comparisons** - `.replace(tzinfo=None)`
- **Wrap in try/except** - graceful degradation if comparison fails
- **Document your choice** - either all TZ-aware or all TZ-naive

### 3. Testing Agent Code

- **Test internal methods directly** - `_parse_json_response()`, `_build_extraction_result()`
- **Dedicate test class to safety invariants** - `TestIntakeAgentSafetyInvariants`
- **Test evaluators separately** - don't need LLM calls to test eval logic

---

## Related Documentation

- [CLAUDE.md](/CLAUDE.md) - AI safety boundaries and architecture principles
- [README.md](/README.md) - Sprint 3 feature list
- [IMPLEMENTATION_COMPLETE.md](/IMPLEMENTATION_COMPLETE.md) - Implementation status

---

## Commits

- `09f6376` - feat(sprint3): Add agentic coprocessor with full observability
- `45282da` - docs: Update README and IMPLEMENTATION_COMPLETE for Sprint 3
