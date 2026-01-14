"""
Evals Module - Evaluation framework for AI outputs.

Ensures AI agents produce grounded, faithful outputs.
CI integration: exit 1 on any failure.

Validators:
- GroundingValidator: All claims must reference valid evidence IDs
- HallucinationDetector: No unsupported claims allowed

Usage:
    python -m evals.runner  # Runs all evals, exits 1 on failure
"""

from .validators.grounding import GroundingValidator, GroundingResult
from .validators.hallucination import HallucinationDetector, HallucinationResult
from .runner import EvalRunner

__all__ = [
    "GroundingValidator",
    "GroundingResult",
    "HallucinationDetector",
    "HallucinationResult",
    "EvalRunner",
]
