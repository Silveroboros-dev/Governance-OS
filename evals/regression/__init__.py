"""
Kernel Regression Evals - Sprint 3

Tests deterministic kernel outputs against historical decisions.
Detects policy drift by replaying decisions and comparing results.
"""

from .evaluator import RegressionEvaluator

__all__ = ["RegressionEvaluator"]
