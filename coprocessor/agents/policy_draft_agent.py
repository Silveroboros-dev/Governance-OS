"""
PolicyDraftAgent - Generates draft policy versions from natural language.

Sprint 3: This agent creates policy drafts for human review via approval queue.

Uses Gemini 3 with Context Caching for:
- 90% cost reduction on cached prompts/vocabularies
- 40-50% latency reduction
- Automatic cache refresh on policy changes

SAFETY INVARIANTS:
1. Rule definitions must be deterministically evaluatable
2. Only use signal types from target pack vocabulary
3. Never auto-approve - all drafts go to approval queue
4. Include test scenarios showing expected behavior
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas.policy_draft import (
    PolicyDraft,
    PolicyDraftResult,
    TestScenario,
    validate_rule_definition,
)
from ..schemas.extraction import get_valid_signal_types
from ..cache import GeminiClient, get_cache_manager


class PolicyDraftAgent:
    """
    Agent that generates draft policies from natural language descriptions.

    All outputs are schema-validated and sent to approval queue.
    Uses Gemini 3 Context Caching for enterprise-grade efficiency.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-flash-preview",
        use_cache: bool = True,
    ):
        """
        Initialize the PolicyDraftAgent.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Gemini 3 model to use
            use_cache: Whether to use context caching (default True)
        """
        self._client = GeminiClient(api_key=api_key, model=model)
        self._use_cache = use_cache
        self._cache_manager = get_cache_manager() if use_cache else None

        # Load system prompt
        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_path = prompts_dir / "policy_draft_system.txt"
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found."""
        return """You are a PolicyDraftAgent. Generate deterministic policy rules from descriptions.
Rules must be evaluatable and include test scenarios."""

    def _ensure_cache(self, pack: str) -> Optional[str]:
        """Ensure cache exists for this pack, return cache name."""
        if not self._use_cache or not self._cache_manager:
            return None

        cache_name = self._cache_manager.get_cache_name("policy_draft", pack)
        if not cache_name:
            cache_name = self._cache_manager.build_cache("policy_draft", pack)

        return cache_name

    async def generate_draft(
        self,
        description: str,
        pack: str,
        existing_policy_id: Optional[str] = None,
        existing_policy_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> PolicyDraftResult:
        """
        Generate a policy draft from a natural language description.

        Args:
            description: Natural language policy description
            pack: Target pack (treasury/wealth)
            existing_policy_id: Policy ID if updating existing policy
            existing_policy_context: Context about existing policy if updating
            trace_id: Optional trace ID for observability

        Returns:
            PolicyDraftResult with the generated draft
        """
        # Get valid signal types for pack
        valid_signal_types = get_valid_signal_types(pack)
        if not valid_signal_types:
            return PolicyDraftResult(
                draft=PolicyDraft(
                    name="Invalid",
                    description="Invalid pack",
                    rule_definition={"type": "invalid"},
                    signal_types_referenced=[],
                    change_reason="Error",
                    pack=pack,
                ),
                validation_errors=[f"Unknown pack: {pack}"]
            )

        # Build the prompt
        context = ""
        if existing_policy_context:
            context = f"""
Existing Policy Context (you are updating this policy):
{json.dumps(existing_policy_context, indent=2)}
"""

        user_prompt = f"""Generate a policy draft for the following requirements:

{description}

Target Pack: {pack}
{context}

Valid signal types for {pack} pack:
{json.dumps(valid_signal_types, indent=2)}

Requirements:
1. Create a deterministic rule definition
2. Reference only the signal types listed above
3. Include at least 2 test scenarios
4. Explain your reasoning in draft_notes

Return a valid JSON object following the schema."""

        # Generate response (with or without caching)
        cache_name = self._ensure_cache(pack)

        if cache_name:
            response_text = self._client.generate_with_cache(
                cache_name=cache_name,
                user_prompt=user_prompt,
                max_tokens=4000,
                temperature=0.1,
            )
        else:
            response_text = self._client.generate(
                user_prompt=user_prompt,
                system_prompt=self.system_prompt,
                max_tokens=4000,
                temperature=0.1,
            )

        # Parse the response
        draft_data = self._parse_json_response(response_text)

        # Build and validate the draft
        return self._build_draft_result(
            draft_data=draft_data,
            pack=pack,
            existing_policy_id=existing_policy_id,
            valid_signal_types=valid_signal_types,
        )

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Handle markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    def _build_draft_result(
        self,
        draft_data: Dict[str, Any],
        pack: str,
        existing_policy_id: Optional[str],
        valid_signal_types: List[str],
    ) -> PolicyDraftResult:
        """Build and validate PolicyDraftResult from parsed data."""
        validation_errors = []

        # Build test scenarios
        test_scenarios = []
        for scenario_data in draft_data.get("test_scenarios", []):
            try:
                test_scenarios.append(TestScenario(
                    description=scenario_data.get("description", ""),
                    input_signals=scenario_data.get("input_signals", []),
                    expected_result=scenario_data.get("expected_result", "pass"),
                    expected_exception_severity=scenario_data.get("expected_exception_severity"),
                    notes=scenario_data.get("notes"),
                ))
            except Exception as e:
                validation_errors.append(f"Invalid test scenario: {e}")

        # Validate rule definition
        rule_def = draft_data.get("rule_definition", {})
        rule_errors = validate_rule_definition(rule_def, pack, valid_signal_types)
        validation_errors.extend(rule_errors)

        # Validate signal types referenced
        signal_types = draft_data.get("signal_types_referenced", [])
        for st in signal_types:
            if st not in valid_signal_types:
                validation_errors.append(f"Unknown signal type referenced: {st}")

        # Build the draft
        try:
            draft = PolicyDraft(
                name=draft_data.get("name", "Unnamed Policy"),
                description=draft_data.get("description", ""),
                rule_definition=rule_def,
                signal_types_referenced=signal_types,
                change_reason=draft_data.get("change_reason", "Generated by agent"),
                pack=pack,
                draft_notes=draft_data.get("draft_notes"),
                test_scenarios=test_scenarios,
                policy_id=existing_policy_id,
            )
        except Exception as e:
            validation_errors.append(f"Failed to create draft: {e}")
            draft = PolicyDraft(
                name="Invalid",
                description="Failed to parse",
                rule_definition={"type": "invalid"},
                signal_types_referenced=[],
                change_reason="Error",
                pack=pack,
            )

        return PolicyDraftResult(
            draft=draft,
            validation_errors=validation_errors,
        )

    def generate_draft_sync(
        self,
        description: str,
        pack: str,
        existing_policy_id: Optional[str] = None,
        existing_policy_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> PolicyDraftResult:
        """Synchronous version of generate_draft."""
        import asyncio
        return asyncio.run(self.generate_draft(
            description, pack, existing_policy_id, existing_policy_context, trace_id
        ))

    async def generate_and_propose(
        self,
        description: str,
        pack: str,
        existing_policy_id: Optional[str] = None,
        existing_policy_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        mcp_client=None,
    ) -> Dict[str, Any]:
        """
        Generate a policy draft and propose it via MCP.

        Args:
            description: Natural language policy description
            pack: Target pack
            existing_policy_id: Policy ID if updating
            existing_policy_context: Context about existing policy
            trace_id: Optional trace ID
            mcp_client: MCP client for proposing

        Returns:
            Dict with draft result and approval ID
        """
        # Generate draft
        result = await self.generate_draft(
            description=description,
            pack=pack,
            existing_policy_id=existing_policy_id,
            existing_policy_context=existing_policy_context,
            trace_id=trace_id,
        )

        # Propose via MCP if no validation errors
        approval_id = None
        if not result.validation_errors and mcp_client:
            try:
                proposal_result = await mcp_client.call_tool(
                    "propose_policy_draft",
                    {
                        "name": result.draft.name,
                        "description": result.draft.description,
                        "rule_definition": result.draft.rule_definition,
                        "signal_types_referenced": result.draft.signal_types_referenced,
                        "change_reason": result.draft.change_reason,
                        "pack": pack,
                        "draft_notes": result.draft.draft_notes,
                        "test_scenarios": [
                            {
                                "description": s.description,
                                "input_signals": s.input_signals,
                                "expected_result": s.expected_result,
                                "expected_exception_severity": s.expected_exception_severity,
                                "notes": s.notes,
                            }
                            for s in result.draft.test_scenarios
                        ],
                        "policy_id": existing_policy_id,
                        "trace_id": trace_id,
                    }
                )
                approval_id = proposal_result.get("approval_id")
            except Exception as e:
                result.validation_errors.append(f"Failed to propose: {e}")

        result.approval_id = approval_id
        return {
            "draft_result": result,
            "approval_id": approval_id,
            "has_validation_errors": len(result.validation_errors) > 0,
            "test_scenario_count": len(result.draft.test_scenarios),
        }

    def validate_draft(
        self,
        draft: PolicyDraft,
    ) -> List[str]:
        """
        Validate a policy draft.

        Args:
            draft: PolicyDraft to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        valid_signal_types = get_valid_signal_types(draft.pack)

        # Validate rule definition
        rule_errors = validate_rule_definition(
            draft.rule_definition,
            draft.pack,
            valid_signal_types
        )
        errors.extend(rule_errors)

        # Validate signal types
        for st in draft.signal_types_referenced:
            if st not in valid_signal_types:
                errors.append(f"Unknown signal type: {st}")

        # Check for test scenarios
        if len(draft.test_scenarios) < 2:
            errors.append("At least 2 test scenarios required")

        return errors
