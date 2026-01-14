"""
Coprocessor Agents - AI agents for governance assistance.

Available agents:
- NarrativeAgent: Drafts memos grounded to evidence IDs
"""

from .narrative_agent import NarrativeAgent

__all__ = ["NarrativeAgent"]
