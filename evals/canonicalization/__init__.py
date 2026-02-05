"""
Canonicalization Evals.

A/B comparison of raw extraction vs canonicalized signals.
Measures false breach reduction, duplicate detection, cross-model stability.
"""

from .evaluator import CanonicalizationEvaluator

__all__ = ["CanonicalizationEvaluator"]
