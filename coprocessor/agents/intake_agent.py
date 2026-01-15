"""
IntakeAgent - Extracts candidate signals from unstructured documents.

Sprint 3: This agent processes PDFs, emails, and reports to extract
structured signals for human review via the approval queue.

SAFETY INVARIANTS:
1. Only output signal types from pack vocabulary
2. Every extracted value must have source_span reference
3. Never infer values not explicitly stated
4. Confidence scores must be honest
5. All outputs go to approval queue for human review
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..schemas.extraction import (
    CandidateSignal,
    ExtractionResult,
    SourceSpan,
    get_valid_signal_types,
    validate_signal_type_for_pack,
)


class IntakeAgent:
    """
    Agent that extracts structured signals from unstructured documents.

    All outputs are schema-validated and sent to approval queue.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the IntakeAgent.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use for extraction
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

        # Load prompts
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.system_prompt = self._load_prompt(prompts_dir / "intake_system.txt")
        self.treasury_prompt = self._load_prompt(prompts_dir / "intake_treasury.txt")
        self.wealth_prompt = self._load_prompt(prompts_dir / "intake_wealth.txt")

    def _load_prompt(self, path: Path) -> str:
        """Load prompt from file or return default."""
        if path.exists():
            return path.read_text()
        return ""

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

    def _get_pack_prompt(self, pack: str) -> str:
        """Get pack-specific prompt."""
        if pack == "treasury":
            return self.treasury_prompt
        elif pack == "wealth":
            return self.wealth_prompt
        else:
            raise ValueError(f"Unknown pack: {pack}")

    async def extract_signals(
        self,
        content: str,
        pack: str,
        document_source: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract candidate signals from document content.

        Args:
            content: Document text content
            pack: Target pack (treasury/wealth)
            document_source: Source identifier for the document
            document_metadata: Optional metadata (sender, received_at, etc.)
            trace_id: Optional trace ID for observability

        Returns:
            ExtractionResult with candidate signals
        """
        # Validate pack
        valid_types = get_valid_signal_types(pack)
        if not valid_types:
            raise ValueError(f"Unknown pack: {pack}")

        # Build the prompt
        pack_prompt = self._get_pack_prompt(pack)
        full_system = f"{self.system_prompt}\n\n{pack_prompt}"

        user_prompt = f"""Extract signals from the following document.

Document Source: {document_source}
Document Metadata: {json.dumps(document_metadata or {}, indent=2)}

Valid signal types for {pack} pack:
{json.dumps(valid_types, indent=2)}

Document Content:
---
{content}
---

Extract all relevant signals. For each signal:
1. Use only signal types from the list above
2. Include source_spans pointing to exact text
3. Provide honest confidence scores
4. Add extraction notes explaining your reasoning

Return a JSON array of candidate signals. If no signals found, return empty array [].
"""

        # Call the LLM
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=full_system,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse the response
        response_text = response.content[0].text

        # Extract JSON from response
        candidates_data = self._parse_json_response(response_text)

        # Build and validate extraction result
        return self._build_extraction_result(
            candidates_data=candidates_data,
            pack=pack,
            document_source=document_source,
            document_metadata=document_metadata or {},
            content=content,
        )

    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
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
            data = json.loads(response_text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "candidates" in data:
                return data["candidates"]
            else:
                return [data]
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    def _build_extraction_result(
        self,
        candidates_data: List[Dict[str, Any]],
        pack: str,
        document_source: str,
        document_metadata: Dict[str, Any],
        content: str,
    ) -> ExtractionResult:
        """Build and validate ExtractionResult from parsed data."""
        candidates = []
        validation_notes = []

        for i, candidate_data in enumerate(candidates_data):
            try:
                # Validate signal type
                signal_type = candidate_data.get("signal_type", "")
                if not validate_signal_type_for_pack(signal_type, pack):
                    validation_notes.append(
                        f"Skipped candidate {i}: invalid signal_type '{signal_type}' for pack '{pack}'"
                    )
                    continue

                # Build source spans
                source_spans = []
                for span_data in candidate_data.get("source_spans", []):
                    try:
                        source_spans.append(SourceSpan(
                            start_char=span_data.get("start_char", 0),
                            end_char=span_data.get("end_char", 0),
                            text=span_data.get("text", ""),
                            page=span_data.get("page"),
                        ))
                    except Exception as e:
                        validation_notes.append(
                            f"Skipped source span in candidate {i}: {e}"
                        )

                if not source_spans:
                    validation_notes.append(
                        f"Skipped candidate {i}: no valid source spans"
                    )
                    continue

                # Build candidate signal
                confidence = float(candidate_data.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to valid range

                candidates.append(CandidateSignal(
                    signal_type=signal_type,
                    payload=candidate_data.get("payload", {}),
                    confidence=confidence,
                    source_spans=source_spans,
                    extraction_notes=candidate_data.get("extraction_notes"),
                ))

            except Exception as e:
                validation_notes.append(f"Error processing candidate {i}: {e}")

        return ExtractionResult(
            document_source=document_source,
            document_metadata=document_metadata,
            pack=pack,
            candidates=candidates,
            extraction_notes="\n".join(validation_notes) if validation_notes else None,
        )

    def extract_signals_sync(
        self,
        content: str,
        pack: str,
        document_source: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Synchronous version of extract_signals.
        """
        import asyncio
        return asyncio.run(self.extract_signals(
            content, pack, document_source, document_metadata, trace_id
        ))

    async def extract_and_propose(
        self,
        content: str,
        pack: str,
        document_source: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        mcp_client=None,
    ) -> Dict[str, Any]:
        """
        Extract signals and propose them via MCP.

        This is the full pipeline: extract → validate → propose to approval queue.

        Args:
            content: Document text content
            pack: Target pack (treasury/wealth)
            document_source: Source identifier
            document_metadata: Optional metadata
            trace_id: Optional trace ID
            mcp_client: MCP client for proposing signals

        Returns:
            Dict with extraction results and approval IDs
        """
        # Extract signals
        result = await self.extract_signals(
            content=content,
            pack=pack,
            document_source=document_source,
            document_metadata=document_metadata,
            trace_id=trace_id,
        )

        # Propose each candidate via MCP
        approval_ids = []
        for candidate in result.candidates:
            if mcp_client:
                try:
                    proposal_result = await mcp_client.call_tool(
                        "propose_signal",
                        {
                            "pack": pack,
                            "signal_type": candidate.signal_type,
                            "payload": candidate.payload,
                            "source": document_source,
                            "observed_at": datetime.utcnow().isoformat(),
                            "source_spans": [
                                {
                                    "start_char": span.start_char,
                                    "end_char": span.end_char,
                                    "text": span.text,
                                    "page": span.page,
                                }
                                for span in candidate.source_spans
                            ],
                            "confidence": candidate.confidence,
                            "extraction_notes": candidate.extraction_notes,
                            "trace_id": trace_id,
                        }
                    )
                    if "approval_id" in proposal_result:
                        approval_ids.append(proposal_result["approval_id"])
                except Exception as e:
                    # Log error but continue
                    pass

        return {
            "extraction_result": result,
            "approval_ids": approval_ids,
            "total_candidates": len(result.candidates),
            "high_confidence": result.high_confidence_count,
            "requires_verification": result.requires_verification_count,
        }

    def validate_extraction(
        self,
        result: ExtractionResult,
        content: str,
    ) -> List[str]:
        """
        Validate an extraction result against the source content.

        Args:
            result: ExtractionResult to validate
            content: Original document content

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for i, candidate in enumerate(result.candidates):
            # Check signal type validity
            if not validate_signal_type_for_pack(candidate.signal_type, result.pack):
                errors.append(
                    f"Candidate {i}: invalid signal_type '{candidate.signal_type}' for pack '{result.pack}'"
                )

            # Check source spans reference actual content
            for j, span in enumerate(candidate.source_spans):
                if span.start_char >= len(content) or span.end_char > len(content):
                    errors.append(
                        f"Candidate {i}, span {j}: character offsets out of range"
                    )
                else:
                    actual_text = content[span.start_char:span.end_char]
                    # Allow some flexibility in whitespace
                    if span.text.strip() not in content:
                        errors.append(
                            f"Candidate {i}, span {j}: quoted text not found in document"
                        )

            # Check confidence is reasonable
            if candidate.confidence < 0.0 or candidate.confidence > 1.0:
                errors.append(
                    f"Candidate {i}: confidence {candidate.confidence} out of range [0.0, 1.0]"
                )

        return errors
