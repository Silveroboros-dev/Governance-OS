# feat: Sprint 3 - Agentic Coprocessor MVP

**Type:** Enhancement
**Priority:** High
**Complexity:** Medium (4 weeks)
**Status:** MVP-scoped

---

## Overview

Sprint 3 delivers the **minimum viable agentic layer**: NarrativeAgent UI integration, a simple approval queue, and IntakeAgent for document extraction. We ship fast, validate with real users, then add infrastructure based on actual pain points.

**Core Principle:** Zero customers means zero enterprise infrastructure. Build only what's needed to test the hypothesis.

---

## Hypothesis to Validate

> "Can AI extract structured signals from unstructured documents with enough accuracy that humans trust it enough to approve them?"

**Success criteria:** >50% approval rate on real documents + users say "this saved me time"

---

## MVP Scope (What We're Building)

| Week | Deliverable | Value |
|------|-------------|-------|
| 1 | NarrativeAgent UI integration | Instant summaries for any decision |
| 2 | Minimal approval queue | Humans can approve/reject proposals |
| 3 | IntakeAgent + propose_signal | Extract signals from documents |
| 4 | Validation with real data | Learn if hypothesis is valid |

**Total: ~550 lines of new code**

---

## What We're NOT Building (Deferred)

| Feature | Why Deferred |
|---------|--------------|
| AgentTrace table | Use console.log until we have production bugs |
| Tracing viewer UI | No users to debug yet |
| PolicyDraftAgent | No customer request; policies created weekly |
| ECE calibration metrics | Need 100+ samples for statistical significance |
| `dismiss_exception` tool | Contradicts human-in-the-loop principle |
| `list_my_proposals` tool | Agent self-awareness is v2 |
| `get_pack_vocabulary` tool | Hardcode in prompt |
| JWT authentication | No external users yet |
| Proposal expiration | Manual cleanup is fine |
| Optimistic locking | One approver is fine for MVP |

---

## Technical Approach

### Architecture (Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                             │
│  ┌────────────────┐           ┌────────────────┐            │
│  │ NarrativeAgent │           │  IntakeAgent   │            │
│  │ (read-only)    │           │ (proposes)     │            │
│  └───────┬────────┘           └───────┬────────┘            │
│          │                            │                      │
│          │                    ┌───────▼───────┐              │
│          │                    │ propose_signal│              │
│          │                    │ MCP tool      │              │
│          │                    └───────┬───────┘              │
└──────────┼────────────────────────────┼──────────────────────┘
           │                            │
           │                    ┌───────▼───────┐
           │                    │ Approval      │
           │                    │ Queue         │
           │                    └───────┬───────┘
           │                            │
           │                    ┌───────▼───────┐
           │                    │ Human Review  │
           │                    │ (approve/     │
           │                    │  reject)      │
           │                    └───────┬───────┘
           │                            │
┌──────────┼────────────────────────────┼──────────────────────┐
│          │                            │                      │
│  ┌───────▼───────┐            ┌───────▼───────┐              │
│  │ Evidence Pack │            │ Signal        │              │
│  │ (existing)    │            │ (if approved) │              │
│  └───────────────┘            └───────────────┘              │
│                                                              │
│              Deterministic Governance Kernel                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Week 1: NarrativeAgent UI Integration

**Objective:** Make NarrativeAgent (already built in Sprint 2) useful from day 1.

**Why first:** No new infrastructure needed. Immediate value on existing decisions.

### Tasks

- [ ] Add "Generate Summary" button to decision trace view
- [ ] Create `/api/v1/narrative/{decision_id}` endpoint
- [ ] Display NarrativeMemo in decision detail
- [ ] Add "Copy as Markdown" / "Export" options

### Files to Create/Modify

```python
# core/api/routers/narrative.py
"""
Narrative generation endpoint.

Wraps NarrativeAgent to generate grounded memos for decisions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.services.evidence_generator import EvidenceGenerator
from coprocessor.agents.narrative_agent import NarrativeAgent

router = APIRouter(prefix="/narrative", tags=["narrative"])


@router.post("/{decision_id}")
async def generate_narrative(
    decision_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generate a grounded narrative memo for a decision.

    Returns both structured memo and markdown format.
    """
    # Get evidence pack
    evidence_gen = EvidenceGenerator(db)
    try:
        evidence_pack = evidence_gen.get_evidence_pack_dict(decision_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Decision not found: {e}")

    # Generate narrative
    agent = NarrativeAgent()
    memo = await agent.draft_memo(str(decision_id), evidence_pack)

    # Validate grounding
    errors = agent.validate_grounding(memo, evidence_pack)

    return {
        "memo": memo.model_dump(),
        "markdown": agent.format_memo_markdown(memo),
        "grounding_errors": errors,
    }
```

```typescript
// ui/components/decisions/NarrativeButton.tsx
'use client'

import { useState } from 'react'
import { FileText, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface NarrativeButtonProps {
  decisionId: string
}

export function NarrativeButton({ decisionId }: NarrativeButtonProps) {
  const [loading, setLoading] = useState(false)
  const [memo, setMemo] = useState<{ markdown: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const generate = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/v1/narrative/${decisionId}`, {
        method: 'POST',
      })
      const data = await res.json()
      setMemo(data)
    } finally {
      setLoading(false)
    }
  }

  const copyMarkdown = () => {
    if (memo?.markdown) {
      navigator.clipboard.writeText(memo.markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (memo) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">Generated Summary</h3>
          <Button variant="ghost" size="sm" onClick={copyMarkdown}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
        <div className="prose prose-sm max-w-none bg-muted p-4 rounded-lg">
          <pre className="whitespace-pre-wrap text-sm">{memo.markdown}</pre>
        </div>
      </div>
    )
  }

  return (
    <Button onClick={generate} disabled={loading}>
      <FileText className="h-4 w-4 mr-2" />
      {loading ? 'Generating...' : 'Generate Summary'}
    </Button>
  )
}
```

### Success Criteria

- [ ] Can generate narrative for any existing decision
- [ ] Memo displays with evidence citations
- [ ] Can copy markdown to clipboard
- [ ] No ungrounded claims (validation passes)

---

## Week 2: Minimal Approval Queue

**Objective:** Simple infrastructure for human-in-the-loop approval.

### Database Schema (Simplified)

```python
# core/models/proposal.py
"""
Minimal approval queue for agent proposals.

8 columns, not 20. No optimistic locking, no expiration, no tracing FK.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class PendingProposal(Base):
    """
    Queue for agent actions requiring human approval.

    MVP: Only signal proposals. Policy proposals deferred.
    """
    __tablename__ = "pending_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    proposal_type = Column(String(50), nullable=False)  # "signal" for now
    pack = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)  # signal_type, payload, source, source_spans
    confidence = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    proposed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PendingProposal(id={self.id}, status={self.status})>"
```

### API Endpoints

```python
# core/api/routers/proposals.py
"""
Approval queue API endpoints.

Simple CRUD: create, list, approve, reject.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.models.proposal import PendingProposal
from core.models.signal import Signal
from core.models.audit import AuditEvent

router = APIRouter(prefix="/proposals", tags=["proposals"])


class CreateProposalRequest(BaseModel):
    proposal_type: str = "signal"
    pack: str
    payload: dict
    confidence: float | None = None


class ApproveRequest(BaseModel):
    decided_by: str


class RejectRequest(BaseModel):
    decided_by: str
    reason: str


@router.post("")
def create_proposal(req: CreateProposalRequest, db: Session = Depends(get_db)):
    """Create a new proposal for review."""
    proposal = PendingProposal(
        proposal_type=req.proposal_type,
        pack=req.pack,
        payload=req.payload,
        confidence=req.confidence,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {"id": str(proposal.id), "status": "pending"}


@router.get("")
def list_proposals(
    pack: str,
    status: str = "pending",
    db: Session = Depends(get_db)
):
    """List proposals filtered by pack and status."""
    proposals = db.query(PendingProposal).filter(
        PendingProposal.pack == pack,
        PendingProposal.status == status,
    ).order_by(PendingProposal.proposed_at.desc()).all()

    return [
        {
            "id": str(p.id),
            "proposal_type": p.proposal_type,
            "payload": p.payload,
            "confidence": p.confidence,
            "proposed_at": p.proposed_at.isoformat(),
        }
        for p in proposals
    ]


@router.post("/{proposal_id}/approve")
def approve_proposal(
    proposal_id: UUID,
    req: ApproveRequest,
    db: Session = Depends(get_db)
):
    """Approve a proposal and create the resulting entity."""
    proposal = db.query(PendingProposal).filter(
        PendingProposal.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal already {proposal.status}")

    # Create the signal
    payload = proposal.payload
    signal = Signal(
        pack=proposal.pack,
        signal_type=payload["signal_type"],
        payload=payload.get("payload", {}),
        source=payload.get("source", "agent_extraction"),
        received_at=datetime.now(timezone.utc),
    )
    db.add(signal)

    # Update proposal
    proposal.status = "approved"
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decided_by = req.decided_by

    # Audit event
    audit = AuditEvent(
        event_type="proposal_approved",
        entity_type="signal",
        entity_id=signal.id,
        actor=req.decided_by,
        details={"proposal_id": str(proposal_id)},
    )
    db.add(audit)

    db.commit()
    return {"status": "approved", "signal_id": str(signal.id)}


@router.post("/{proposal_id}/reject")
def reject_proposal(
    proposal_id: UUID,
    req: RejectRequest,
    db: Session = Depends(get_db)
):
    """Reject a proposal with reason."""
    proposal = db.query(PendingProposal).filter(
        PendingProposal.id == proposal_id
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal already {proposal.status}")

    proposal.status = "rejected"
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decided_by = req.decided_by
    proposal.rejection_reason = req.reason

    db.commit()
    return {"status": "rejected"}
```

### Approval UI

```typescript
// ui/app/proposals/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import { usePack } from '@/lib/pack-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Proposal {
  id: string
  proposal_type: string
  payload: {
    signal_type: string
    payload: Record<string, unknown>
    source_spans?: Array<{ quoted_text: string }>
  }
  confidence: number | null
  proposed_at: string
}

export default function ProposalsPage() {
  const { pack } = usePack()
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/v1/proposals?pack=${pack}&status=pending`)
      .then(res => res.json())
      .then(data => {
        setProposals(data)
        setLoading(false)
      })
  }, [pack])

  const approve = async (id: string) => {
    await fetch(`/api/v1/proposals/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decided_by: 'user@example.com' }),
    })
    setProposals(proposals.filter(p => p.id !== id))
  }

  const reject = async (id: string, reason: string) => {
    await fetch(`/api/v1/proposals/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decided_by: 'user@example.com', reason }),
    })
    setProposals(proposals.filter(p => p.id !== id))
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Pending Proposals</h1>

      {proposals.length === 0 ? (
        <p className="text-muted-foreground">No pending proposals</p>
      ) : (
        <div className="space-y-4">
          {proposals.map(proposal => (
            <Card key={proposal.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{proposal.payload.signal_type}</span>
                  {proposal.confidence && (
                    <span className="text-sm font-normal text-muted-foreground">
                      {Math.round(proposal.confidence * 100)}% confidence
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-sm bg-muted p-2 rounded mb-4">
                  {JSON.stringify(proposal.payload.payload, null, 2)}
                </pre>

                {proposal.payload.source_spans?.map((span, i) => (
                  <blockquote key={i} className="border-l-2 pl-4 italic text-sm mb-2">
                    "{span.quoted_text}"
                  </blockquote>
                ))}

                <div className="flex gap-2 mt-4">
                  <Button onClick={() => approve(proposal.id)}>
                    <Check className="h-4 w-4 mr-2" /> Approve
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => reject(proposal.id, 'Incorrect extraction')}
                  >
                    <X className="h-4 w-4 mr-2" /> Reject
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Success Criteria

- [ ] Can create proposals via API
- [ ] Can list pending proposals filtered by pack
- [ ] Approve creates Signal + AuditEvent
- [ ] Reject stores reason
- [ ] UI shows pending proposals with approve/reject buttons

---

## Week 3: IntakeAgent + propose_signal

**Objective:** Extract signals from documents and propose them for approval.

### IntakeAgent (Simplified)

```python
# coprocessor/agents/intake_agent.py
"""
IntakeAgent - Extracts candidate signals from unstructured documents.

MVP: Simple extraction with source spans. No confidence calibration.
"""

import json
import os
from typing import Any

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    """Grounding evidence from source document."""
    quoted_text: str = Field(..., min_length=1)


class CandidateSignal(BaseModel):
    """Signal extracted by IntakeAgent."""
    signal_type: str
    payload: dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_spans: list[SourceSpan] = Field(..., min_length=1)


class IntakeAgent:
    """Extracts candidate signals from unstructured documents."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def extract(
        self,
        document_content: str,
        pack: str,
    ) -> list[CandidateSignal]:
        """
        Extract candidate signals from document.

        Args:
            document_content: Text content of the document
            pack: Target pack for signal type vocabulary

        Returns:
            List of CandidateSignal objects with source spans
        """
        # Hardcoded vocabulary (MVP - no dynamic lookup)
        if pack == "treasury":
            signal_types = """
            - position_limit_breach: Position exceeds approved limit
            - market_volatility_spike: Volatility threshold exceeded
            - counterparty_credit_downgrade: Credit rating change
            - liquidity_threshold_breach: Liquidity below threshold
            """
        else:
            signal_types = """
            - portfolio_drift: Allocation drift from target
            - risk_score_change: Client risk profile change
            - rebalancing_trigger: Rebalancing threshold crossed
            """

        system = f"""You are an extraction agent for Governance OS ({pack} pack).

Extract structured signals from documents. Available signal types:
{signal_types}

RULES:
1. EVERY extracted value MUST have source_spans with EXACT quoted text
2. Only extract signal types from the list above
3. Never infer values - only extract what is explicitly stated
4. Be conservative with confidence

Output JSON:
{{
  "signals": [
    {{
      "signal_type": "...",
      "payload": {{}},
      "confidence": 0.8,
      "source_spans": [{{"quoted_text": "exact quote from document"}}]
    }}
  ]
}}"""

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": f"Extract signals:\n\n{document_content}"}],
        )

        # Parse response
        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text)

        signals = []
        for item in data.get("signals", []):
            try:
                signal = CandidateSignal(
                    signal_type=item["signal_type"],
                    payload=item.get("payload", {}),
                    confidence=item.get("confidence", 0.5),
                    source_spans=[
                        SourceSpan(quoted_text=s["quoted_text"])
                        for s in item.get("source_spans", [])
                    ],
                )
                signals.append(signal)
            except Exception:
                continue  # Skip invalid extractions

        return signals

    def validate_spans(
        self,
        signals: list[CandidateSignal],
        original_content: str,
    ) -> list[str]:
        """Validate that source spans exist in document."""
        errors = []
        for i, signal in enumerate(signals):
            for j, span in enumerate(signal.source_spans):
                if span.quoted_text not in original_content:
                    errors.append(f"Signal {i}, span {j}: quoted text not found")
        return errors
```

### propose_signal MCP Tool

```python
# mcp_server/tools/write_tools.py
"""
MCP Write Tools - MVP version with just propose_signal.
"""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from core.database import get_db
from core.models.proposal import PendingProposal


def register_write_tools(mcp: FastMCP):
    """Register write tools with MCP server."""

    @mcp.tool
    def propose_signal(
        pack: str,
        signal_type: str,
        payload: dict[str, Any],
        source: str,
        confidence: float,
        source_spans: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Propose a new signal for human approval.

        REQUIRES APPROVAL: This will be queued for human review.
        The signal is only created if a human approves it.

        Args:
            pack: Domain pack (treasury, wealth)
            signal_type: Signal type from pack vocabulary
            payload: Signal data payload
            source: Source system or document
            confidence: Extraction confidence (0.0-1.0)
            source_spans: Source spans for grounding

        Returns:
            Proposal ID and status
        """
        if not 0.0 <= confidence <= 1.0:
            raise ToolError(f"Confidence must be 0.0-1.0, got {confidence}")

        db = next(get_db())
        try:
            proposal = PendingProposal(
                proposal_type="signal",
                pack=pack,
                payload={
                    "signal_type": signal_type,
                    "payload": payload,
                    "source": source,
                    "source_spans": source_spans or [],
                },
                confidence=confidence,
            )
            db.add(proposal)
            db.commit()
            db.refresh(proposal)

            return {
                "status": "pending_approval",
                "proposal_id": str(proposal.id),
                "message": "Signal queued for human review",
            }
        finally:
            db.close()
```

### Success Criteria

- [ ] IntakeAgent extracts signals from text
- [ ] Every extraction has source spans
- [ ] propose_signal creates PendingProposal
- [ ] Source spans validated against document

---

## Week 4: Validation

**Objective:** Test with real data, measure, decide.

### Tasks

- [ ] Process 10 real treasury documents
- [ ] Measure approval rate
- [ ] Interview users: "Was this useful?"
- [ ] Document rejection reasons
- [ ] Iterate prompts if needed

### Validation Criteria

| Metric | Target | Action if Miss |
|--------|--------|----------------|
| Approval rate | >50% | Improve prompts |
| User satisfaction | "Saved time" | Continue |
| Source span accuracy | >90% | Fix extraction |

### Simple Eval (10 Golden Cases)

```python
# evals/extraction/test_intake.py
"""
Simple extraction tests - 10 golden cases.

No fancy metrics. Just: did it extract the right signals?
"""

import pytest
from coprocessor.agents.intake_agent import IntakeAgent

GOLDEN_CASES = [
    {
        "document": "BTC position at 125% of limit for 5 hours.",
        "pack": "treasury",
        "expected_type": "position_limit_breach",
    },
    {
        "document": "ETH 30-day volatility spiked to 85%, above 70% threshold.",
        "pack": "treasury",
        "expected_type": "market_volatility_spike",
    },
    # ... 8 more cases
]


@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_extraction(case):
    agent = IntakeAgent()
    signals = agent.extract(case["document"], case["pack"])

    assert len(signals) >= 1, "Should extract at least one signal"
    assert any(
        s.signal_type == case["expected_type"] for s in signals
    ), f"Should extract {case['expected_type']}"

    # Verify grounding
    for signal in signals:
        assert len(signal.source_spans) > 0, "Must have source spans"
        errors = agent.validate_spans([signal], case["document"])
        assert len(errors) == 0, f"Source spans must be valid: {errors}"
```

---

## Migration

```python
# db/migrations/versions/006_add_pending_proposals.py
"""
Add pending_proposals table.

MVP: 8 columns, no FK to traces, no expiration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade():
    op.create_table(
        'pending_proposals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('proposal_type', sa.String(50), nullable=False),
        sa.Column('pack', sa.String(50), nullable=False),
        sa.Column('payload', JSONB, nullable=False),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('proposed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.String(255), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
    )

    op.create_index('idx_proposals_pack_status', 'pending_proposals', ['pack', 'status'])


def downgrade():
    op.drop_table('pending_proposals')
```

---

## Files to Create

| File | Purpose | LOC |
|------|---------|-----|
| `core/api/routers/narrative.py` | Narrative generation endpoint | ~40 |
| `ui/components/decisions/NarrativeButton.tsx` | Generate summary button | ~50 |
| `core/models/proposal.py` | PendingProposal model | ~30 |
| `core/api/routers/proposals.py` | Approval queue API | ~100 |
| `ui/app/proposals/page.tsx` | Approval UI | ~80 |
| `coprocessor/agents/intake_agent.py` | IntakeAgent | ~120 |
| `mcp_server/tools/write_tools.py` | propose_signal tool | ~50 |
| `evals/extraction/test_intake.py` | Golden test cases | ~50 |
| `db/migrations/.../006_add_pending_proposals.py` | Migration | ~30 |

**Total: ~550 lines**

---

## Success Metrics

| Metric | Target | When to Measure |
|--------|--------|-----------------|
| Narrative generation works | 100% of decisions | Week 1 |
| Approval flow works | End-to-end | Week 2 |
| Extraction produces signals | >0 per document | Week 3 |
| Approval rate | >50% | Week 4 |
| User says "useful" | Yes | Week 4 |

---

## What Comes Next (Sprint 4, if validated)

Only build these if Sprint 3 validation passes:

- AgentTrace table (if debugging is painful)
- Tracing UI (if users request it)
- ECE calibration (when we have 100+ extractions)
- PolicyDraftAgent (if users request it)
- JWT auth (when we have external users)
- Proposal expiration (if stale proposals become a problem)

---

## References

- Existing NarrativeAgent: `coprocessor/agents/narrative_agent.py`
- Existing MCP server: `mcp_server/server.py`
- Evidence generator: `core/services/evidence_generator.py`
- Signal model: `core/models/signal.py`
