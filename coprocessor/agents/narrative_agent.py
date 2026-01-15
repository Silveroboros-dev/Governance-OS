"""
NarrativeAgent v1 - Drafts memos strictly grounded to evidence IDs.

This agent generates narrative summaries of decisions, but EVERY claim
must reference evidence from the kernel. No unsupported claims allowed.

v1 Features:
- Multi-template support (treasury/wealth-specific templates)
- Short/standard/detailed length variants
- Explicit uncertainty and assumption tracking
- Pack-aware vocabulary

SAFETY INVARIANTS:
1. Never evaluate policies (deterministic kernel only)
2. Never recommend options (symmetric presentation)
3. Every claim must have evidence_refs (grounding required)
4. Never generate severity or escalation assessments
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..schemas.narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
    MemoTemplate,
    MemoTemplateConfig,
    MemoLength,
)


class NarrativeAgent:
    """
    Agent that drafts narrative memos grounded to evidence.

    All outputs are schema-validated and grounding-checked.
    Supports multiple templates and length variants.
    """

    # Valid templates per pack
    PACK_TEMPLATES = {
        "treasury": [
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoTemplate.TREASURY_POSITION,
            MemoTemplate.TREASURY_COUNTERPARTY,
            MemoTemplate.EXECUTIVE_SUMMARY,
            MemoTemplate.DECISION_BRIEF,
        ],
        "wealth": [
            MemoTemplate.WEALTH_SUITABILITY,
            MemoTemplate.WEALTH_PORTFOLIO,
            MemoTemplate.WEALTH_CLIENT,
            MemoTemplate.EXECUTIVE_SUMMARY,
            MemoTemplate.DECISION_BRIEF,
        ],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the NarrativeAgent.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use for generation
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
        self._template_configs: Dict[MemoTemplate, MemoTemplateConfig] = {}

        # Load system prompt
        prompt_path = Path(__file__).parent.parent / "prompts" / "narrative_system.txt"
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text()
        else:
            self.system_prompt = self._default_system_prompt()

        # Load template configurations
        self._load_template_configs()

    def _get_client(self):
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                )
        return self._client

    def _load_template_configs(self):
        """Load template configurations from pack modules."""
        try:
            from packs.treasury.narrative_templates import TREASURY_NARRATIVE_TEMPLATES
            self._template_configs.update(TREASURY_NARRATIVE_TEMPLATES)
        except ImportError:
            pass

        try:
            from packs.wealth.narrative_templates import WEALTH_NARRATIVE_TEMPLATES
            self._template_configs.update(WEALTH_NARRATIVE_TEMPLATES)
        except ImportError:
            pass

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found."""
        return """You are a narrative assistant for Governance OS. Your role is to draft
memos that summarize decisions and their supporting evidence.

CRITICAL RULES:
1. EVERY claim must reference at least one evidence ID
2. NEVER recommend which option to choose - present all options symmetrically
3. NEVER evaluate policies or determine severity - that's the kernel's job
4. Use only facts from the provided evidence pack
5. Format evidence references as [evidence_id]

Output format:
- Title: Brief summary title
- Sections with claims, each claim referencing evidence IDs
- No recommendations, predictions, or opinions"""

    def get_available_templates(self, pack: str) -> List[MemoTemplate]:
        """Get available templates for a pack."""
        return self.PACK_TEMPLATES.get(pack, [MemoTemplate.DECISION_BRIEF])

    def get_template_config(self, template: MemoTemplate) -> Optional[MemoTemplateConfig]:
        """Get configuration for a template."""
        return self._template_configs.get(template)

    def _build_template_prompt(
        self,
        template: MemoTemplate,
        length: MemoLength,
        pack: str,
    ) -> str:
        """Build template-specific instructions for the prompt."""
        config = self.get_template_config(template)
        if not config:
            return ""

        # Get length-specific constraints
        length_config = config.length_guidelines.get(
            length.value,
            {"max_sections": config.max_sections, "max_claims_per_section": config.max_claims_per_section}
        )

        prompt_parts = [
            f"\n## Template: {config.name}",
            f"Description: {config.description}",
            "",
            "## Structure Requirements:",
            f"- Maximum sections: {length_config.get('max_sections', config.max_sections)}",
            f"- Maximum claims per section: {length_config.get('max_claims_per_section', config.max_claims_per_section)}",
        ]

        if config.required_sections:
            prompt_parts.append(f"- Required sections: {', '.join(config.required_sections)}")

        if config.focus_areas:
            prompt_parts.append("\n## Focus Areas:")
            for area in config.focus_areas:
                prompt_parts.append(f"- {area}")

        if config.vocabulary_hints:
            prompt_parts.append(f"\n## Domain Vocabulary (use where appropriate):")
            prompt_parts.append(", ".join(config.vocabulary_hints))

        # Length-specific guidance
        length_guidance = {
            MemoLength.SHORT: "\n## Length: SHORT\nProvide only essential facts. 1-2 paragraphs equivalent. No background or context.",
            MemoLength.STANDARD: "\n## Length: STANDARD\nBalanced detail. Include context and rationale.",
            MemoLength.DETAILED: "\n## Length: DETAILED\nComprehensive coverage. Include all relevant context, timeline, and implications.",
        }
        prompt_parts.append(length_guidance.get(length, ""))

        return "\n".join(prompt_parts)

    async def draft_memo(
        self,
        decision_id: str,
        evidence_pack: Dict[str, Any],
        template: Union[MemoTemplate, str] = MemoTemplate.DECISION_BRIEF,
        length: Union[MemoLength, str] = MemoLength.STANDARD,
        pack: str = "treasury",
    ) -> NarrativeMemo:
        """
        Draft a narrative memo for a decision.

        Args:
            decision_id: ID of the decision
            evidence_pack: Evidence pack from get_evidence_pack MCP tool
            template: Template to use (MemoTemplate enum or string)
            length: Length variant (MemoLength enum or string)
            pack: Pack context (treasury or wealth)

        Returns:
            NarrativeMemo with grounded claims
        """
        # Normalize inputs
        if isinstance(template, str):
            template = MemoTemplate(template)
        if isinstance(length, str):
            length = MemoLength(length)

        # Validate template for pack
        available = self.get_available_templates(pack)
        if template not in available:
            raise ValueError(
                f"Template {template.value} not available for pack {pack}. "
                f"Available: {[t.value for t in available]}"
            )

        # Build the prompt with evidence
        evidence_json = json.dumps(evidence_pack, indent=2, default=str)
        template_instructions = self._build_template_prompt(template, length, pack)

        user_prompt = f"""Draft a narrative memo for decision {decision_id}.
{template_instructions}

Evidence Pack:
{evidence_json}

Requirements:
1. Summarize what happened and why the decision was made
2. Reference specific evidence IDs for every claim
3. Do not recommend or endorse any particular option
4. Keep the memo concise and factual
5. Explicitly note any uncertainties in the evidence
6. State any assumptions you are making

Return a JSON object with this structure:
{{
    "title": "Brief title",
    "sections": [
        {{
            "heading": "Section heading",
            "claims": [
                {{
                    "text": "Claim text",
                    "evidence_refs": ["evidence_id_1", "evidence_id_2"]
                }}
            ]
        }}
    ],
    "uncertainties": ["Any gaps or unclear aspects in the evidence"],
    "assumptions": ["Any assumptions made in interpreting the evidence"]
}}"""

        # Call the LLM
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse the response
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        try:
            memo_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Build the memo with validation
        return self._build_memo(
            decision_id,
            memo_data,
            evidence_pack,
            template=template,
            length=length,
            pack=pack,
        )

    def _build_memo(
        self,
        decision_id: str,
        memo_data: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        template: Optional[MemoTemplate] = None,
        length: Optional[MemoLength] = None,
        pack: Optional[str] = None,
    ) -> NarrativeMemo:
        """Build and validate a NarrativeMemo from parsed data."""
        # Extract available evidence IDs
        available_evidence_ids = set()
        for item in evidence_pack.get("evidence_items", []):
            available_evidence_ids.add(item.get("evidence_id"))

        # Build sections with claims
        sections = []
        for section_data in memo_data.get("sections", []):
            claims = []
            for claim_data in section_data.get("claims", []):
                # Build evidence references
                evidence_refs = []
                for ref_id in claim_data.get("evidence_refs", []):
                    # Find the evidence item
                    evidence_item = None
                    for item in evidence_pack.get("evidence_items", []):
                        if item.get("evidence_id") == ref_id:
                            evidence_item = item
                            break

                    evidence_refs.append(EvidenceReference(
                        evidence_id=ref_id,
                        evidence_type=evidence_item.get("type") if evidence_item else "unknown",
                        excerpt=self._extract_excerpt(evidence_item) if evidence_item else None,
                    ))

                claims.append(NarrativeClaim(
                    text=claim_data.get("text", ""),
                    evidence_refs=evidence_refs,
                ))

            sections.append(MemoSection(
                heading=section_data.get("heading", ""),
                claims=claims,
            ))

        # Build the memo
        memo = NarrativeMemo(
            decision_id=decision_id,
            title=memo_data.get("title", "Decision Summary"),
            sections=sections,
            evidence_pack_id=evidence_pack.get("evidence_pack_id"),
            template_used=template.value if template else None,
            length=length.value if length else "standard",
            pack=pack,
            uncertainties=memo_data.get("uncertainties", []),
            assumptions=memo_data.get("assumptions", []),
        )

        return memo

    def _extract_excerpt(self, evidence_item: Dict[str, Any]) -> Optional[str]:
        """Extract a brief excerpt from evidence for citation."""
        data = evidence_item.get("data", {})

        if evidence_item.get("type") == "signal":
            signal_type = data.get("signal_type", "")
            return f"Signal: {signal_type}"
        elif evidence_item.get("type") == "chosen_option":
            return f"Option: {data.get('label', '')}"
        elif evidence_item.get("type") == "exception_context":
            return f"Context: {json.dumps(data)[:100]}..."
        elif evidence_item.get("type") == "evaluation":
            return f"Evaluation result"
        elif evidence_item.get("type") == "policy":
            return f"Policy: {data.get('name', '')}"

        return None

    def draft_memo_sync(
        self,
        decision_id: str,
        evidence_pack: Dict[str, Any],
        template: Union[MemoTemplate, str] = MemoTemplate.DECISION_BRIEF,
        length: Union[MemoLength, str] = MemoLength.STANDARD,
        pack: str = "treasury",
    ) -> NarrativeMemo:
        """
        Synchronous version of draft_memo.

        Args:
            decision_id: ID of the decision
            evidence_pack: Evidence pack from get_evidence_pack MCP tool
            template: Template to use
            length: Length variant
            pack: Pack context

        Returns:
            NarrativeMemo with grounded claims
        """
        import asyncio
        return asyncio.run(self.draft_memo(
            decision_id,
            evidence_pack,
            template=template,
            length=length,
            pack=pack,
        ))

    def validate_grounding(
        self,
        memo: NarrativeMemo,
        evidence_pack: Dict[str, Any],
    ) -> List[str]:
        """
        Validate that all claims in the memo are properly grounded.

        Args:
            memo: The narrative memo to validate
            evidence_pack: The evidence pack used for grounding

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Get available evidence IDs
        available_ids = {
            item.get("evidence_id")
            for item in evidence_pack.get("evidence_items", [])
        }

        for section in memo.sections:
            for claim in section.claims:
                # Check that claim has evidence refs
                if not claim.evidence_refs:
                    errors.append(
                        f"Ungrounded claim: '{claim.text[:50]}...' has no evidence references"
                    )
                    continue

                # Check that all evidence refs exist
                for ref in claim.evidence_refs:
                    if ref.evidence_id not in available_ids:
                        errors.append(
                            f"Invalid evidence reference: '{ref.evidence_id}' not found in evidence pack"
                        )

        return errors

    def format_memo_markdown(self, memo: NarrativeMemo) -> str:
        """
        Format the memo as markdown with inline citations.

        Args:
            memo: The narrative memo to format

        Returns:
            Markdown-formatted memo
        """
        lines = [
            f"# {memo.title}",
            "",
            f"*Decision ID: {memo.decision_id}*",
            f"*Generated: {memo.generated_at.isoformat()}*",
        ]

        if memo.template_used:
            lines.append(f"*Template: {memo.template_used}*")
        if memo.pack:
            lines.append(f"*Pack: {memo.pack}*")

        lines.append("")

        for section in memo.sections:
            lines.append(f"## {section.heading}")
            lines.append("")

            for claim in section.claims:
                # Format evidence citations
                citations = ", ".join(
                    f"[{ref.evidence_id}]" for ref in claim.evidence_refs
                )
                lines.append(f"- {claim.text} {citations}")

            lines.append("")

        # Add uncertainties if present
        if memo.uncertainties:
            lines.append("---")
            lines.append("## Uncertainties")
            lines.append("")
            for uncertainty in memo.uncertainties:
                lines.append(f"- {uncertainty}")
            lines.append("")

        # Add assumptions if present
        if memo.assumptions:
            lines.append("---")
            lines.append("## Assumptions")
            lines.append("")
            for assumption in memo.assumptions:
                lines.append(f"- {assumption}")
            lines.append("")

        # Add evidence reference section
        lines.append("---")
        lines.append("## Evidence References")
        lines.append("")

        seen_refs = set()
        for section in memo.sections:
            for claim in section.claims:
                for ref in claim.evidence_refs:
                    if ref.evidence_id not in seen_refs:
                        seen_refs.add(ref.evidence_id)
                        excerpt = f": {ref.excerpt}" if ref.excerpt else ""
                        lines.append(f"- **{ref.evidence_id}** ({ref.evidence_type}){excerpt}")

        return "\n".join(lines)

    def select_template_for_exception(
        self,
        exception_context: Dict[str, Any],
        pack: str,
    ) -> MemoTemplate:
        """
        Automatically select the best template for an exception.

        Args:
            exception_context: Exception context from evidence pack
            pack: Pack (treasury or wealth)

        Returns:
            Recommended MemoTemplate
        """
        signal_type = exception_context.get("signal_type", "")

        if pack == "treasury":
            try:
                from packs.treasury.narrative_templates import get_template_for_signal_type
                return get_template_for_signal_type(signal_type)
            except ImportError:
                pass
        elif pack == "wealth":
            try:
                from packs.wealth.narrative_templates import get_template_for_signal_type
                return get_template_for_signal_type(signal_type)
            except ImportError:
                pass

        return MemoTemplate.DECISION_BRIEF
