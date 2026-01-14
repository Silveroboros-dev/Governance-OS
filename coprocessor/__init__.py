"""
Coprocessor Module - AI agents for governance assistance.

SAFETY BOUNDARIES (non-negotiable):
- LLMs NEVER evaluate policies (deterministic kernel only)
- LLMs NEVER decide severity or escalation
- LLMs NEVER recommend options (symmetric presentation)
- All narrative claims MUST reference evidence IDs

Allowed operations:
- Draft memos grounded to evidence IDs
- Extract candidate signals from unstructured data (with provenance)
- Generate policy drafts (never auto-publish)
"""

from .agents.narrative_agent import NarrativeAgent
from .schemas.narrative import NarrativeMemo, NarrativeClaim, EvidenceReference

__all__ = [
    "NarrativeAgent",
    "NarrativeMemo",
    "NarrativeClaim",
    "EvidenceReference",
]
