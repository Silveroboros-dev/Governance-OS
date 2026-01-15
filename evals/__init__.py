"""
Evals Module - Evaluation framework for AI outputs.

Ensures AI agents produce grounded, faithful outputs.
CI integration: exit 1 on any failure.

Validators:
- GroundingValidator: All claims must reference valid evidence IDs
- HallucinationDetector: No unsupported claims allowed

Sprint 3 Evaluators:
- ExtractionEvaluator: Measures IntakeAgent precision/recall/calibration
- RegressionEvaluator: Detects policy drift via replay
- PolicyDraftEvaluator: Validates draft quality and schema compliance

Usage:
    python -m evals.runner  # Runs all evals, exits 1 on failure
    python -m evals.runner --suite extraction --pack treasury
    python -m evals.runner --suite regression --fail-on-drift
"""

from .validators.grounding import GroundingValidator, GroundingResult
from .validators.hallucination import HallucinationDetector, HallucinationResult
from .runner import EvalRunner
from .extraction import ExtractionEvaluator
from .regression import RegressionEvaluator
from .policy_draft import PolicyDraftEvaluator

__all__ = [
    "GroundingValidator",
    "GroundingResult",
    "HallucinationDetector",
    "HallucinationResult",
    "EvalRunner",
    "ExtractionEvaluator",
    "RegressionEvaluator",
    "PolicyDraftEvaluator",
]
