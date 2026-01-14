"""
Hallucination Detector - Detects unsupported claims and forbidden patterns.

Checks for:
1. Claims without evidence references (ungrounded)
2. Forbidden language (recommendations, opinions, severity judgments)
3. Content that implies policy evaluation or option recommendation
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from coprocessor.schemas.narrative import NarrativeMemo


class HallucinationError(BaseModel):
    """A detected hallucination or forbidden pattern."""

    error_type: str
    claim_text: str
    section: Optional[str] = None
    pattern_matched: Optional[str] = None
    message: str


class HallucinationResult(BaseModel):
    """Result of hallucination detection."""

    passed: bool
    total_claims: int = 0
    clean_claims: int = 0
    errors: List[HallucinationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def hallucination_rate(self) -> float:
        """Percentage of claims with detected issues."""
        if self.total_claims == 0:
            return 0.0
        return ((self.total_claims - self.clean_claims) / self.total_claims) * 100


class HallucinationDetector:
    """
    Detects hallucinations and forbidden patterns in narrative memos.

    Forbidden patterns include:
    - Recommendations ("should", "recommend", "best option")
    - Opinions ("I think", "in my view", "appears to be")
    - Severity judgments ("this is critical", "urgent")
    - Unsupported claims (claims without evidence)
    """

    # Patterns that indicate recommendations (FORBIDDEN)
    RECOMMENDATION_PATTERNS = [
        r"\bshould\b",
        r"\brecommend(s|ed|ing)?\b",
        r"\bbest\s+(option|choice|approach)\b",
        r"\boptimal\b",
        r"\badvise\b",
        r"\bsuggest(s|ed|ing)?\b",
        r"\bpropose\b",
        r"\bwould\s+be\s+(better|best)\b",
        r"\bprefer(red|able)?\b",
    ]

    # Patterns that indicate opinions (FORBIDDEN)
    OPINION_PATTERNS = [
        r"\bi\s+think\b",
        r"\bi\s+believe\b",
        r"\bin\s+my\s+(view|opinion)\b",
        r"\bappears?\s+to\s+be\b",
        r"\bseems?\s+(to\s+be|like)\b",
        r"\bprobably\b",
        r"\blikely\b",
        r"\bmight\s+be\b",
        r"\bcould\s+be\b",
    ]

    # Patterns that indicate severity judgments (FORBIDDEN - kernel's job)
    SEVERITY_PATTERNS = [
        r"\bthis\s+is\s+(critical|urgent|serious)\b",
        r"\bimmediately\b",
        r"\brequires?\s+urgent\b",
        r"\bhigh(est)?\s+priority\b",
        r"\bcritical\s+(issue|situation|matter)\b",
    ]

    # Patterns that indicate policy evaluation (FORBIDDEN - kernel's job)
    POLICY_EVAL_PATTERNS = [
        r"\bpolicy\s+(is|was|should\s+be)\s+(too|not|overly)\b",
        r"\bthreshold\s+(is|was|should\s+be)\s+(too|not)\b",
        r"\b(stricter|looser)\s+policy\b",
        r"\bchange\s+the\s+(policy|threshold|limit)\b",
    ]

    def __init__(
        self,
        check_grounding: bool = True,
        custom_forbidden_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the detector.

        Args:
            check_grounding: Also check for ungrounded claims
            custom_forbidden_patterns: Additional regex patterns to check
        """
        self.check_grounding = check_grounding
        self.custom_patterns = custom_forbidden_patterns or []

        # Compile all patterns
        self.compiled_patterns = {
            "recommendation": [re.compile(p, re.IGNORECASE) for p in self.RECOMMENDATION_PATTERNS],
            "opinion": [re.compile(p, re.IGNORECASE) for p in self.OPINION_PATTERNS],
            "severity_judgment": [re.compile(p, re.IGNORECASE) for p in self.SEVERITY_PATTERNS],
            "policy_evaluation": [re.compile(p, re.IGNORECASE) for p in self.POLICY_EVAL_PATTERNS],
            "custom": [re.compile(p, re.IGNORECASE) for p in self.custom_patterns],
        }

    def detect(self, memo: NarrativeMemo) -> HallucinationResult:
        """
        Detect hallucinations in a narrative memo.

        Args:
            memo: The narrative memo to check

        Returns:
            HallucinationResult with detected issues
        """
        result = HallucinationResult(passed=True)

        for section in memo.sections:
            for claim in section.claims:
                result.total_claims += 1
                claim_clean = True

                # Check grounding
                if self.check_grounding and not claim.evidence_refs:
                    result.errors.append(HallucinationError(
                        error_type="ungrounded",
                        claim_text=claim.text,
                        section=section.heading,
                        message=f"Ungrounded claim (no evidence): '{claim.text[:50]}...'"
                    ))
                    result.passed = False
                    claim_clean = False
                    continue

                # Check forbidden patterns
                for pattern_type, patterns in self.compiled_patterns.items():
                    for pattern in patterns:
                        if match := pattern.search(claim.text):
                            result.errors.append(HallucinationError(
                                error_type=pattern_type,
                                claim_text=claim.text,
                                section=section.heading,
                                pattern_matched=match.group(),
                                message=f"Forbidden pattern ({pattern_type}): '{match.group()}' in claim"
                            ))
                            result.passed = False
                            claim_clean = False
                            break  # One match per pattern type is enough

                if claim_clean:
                    result.clean_claims += 1

        return result

    def detect_in_text(self, text: str) -> List[HallucinationError]:
        """
        Detect hallucinations in raw text (not structured memo).

        Args:
            text: Text to check

        Returns:
            List of detected issues
        """
        errors = []

        for pattern_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if match := pattern.search(text):
                    errors.append(HallucinationError(
                        error_type=pattern_type,
                        claim_text=text[:100],
                        pattern_matched=match.group(),
                        message=f"Forbidden pattern ({pattern_type}): '{match.group()}'"
                    ))

        return errors

    def is_clean(self, text: str) -> bool:
        """
        Quick check if text contains any forbidden patterns.

        Args:
            text: Text to check

        Returns:
            True if no forbidden patterns found
        """
        for patterns in self.compiled_patterns.values():
            for pattern in patterns:
                if pattern.search(text):
                    return False
        return True


def detect_hallucinations(
    memo: NarrativeMemo,
    check_grounding: bool = True,
) -> HallucinationResult:
    """
    Convenience function to detect hallucinations in a memo.

    Args:
        memo: The narrative memo to check
        check_grounding: Also check for ungrounded claims

    Returns:
        HallucinationResult with detected issues
    """
    detector = HallucinationDetector(check_grounding=check_grounding)
    return detector.detect(memo)
