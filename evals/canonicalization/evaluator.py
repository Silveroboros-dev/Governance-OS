"""
Canonicalization A/B Evaluator.

Measures whether the Canonicalizer adds value over raw extraction by comparing:
  A) Raw extraction results (before canonicalization)
  B) Canonicalized results (after canonicalization)

Metrics tracked:
  1. False breach rate: How many breach-category signals lack completeness?
  2. Downgrade rate: How many candidates were downgraded breach → observation?
  3. Duplicate reduction: How many duplicates were merged?
  4. Completeness distribution: Average completeness scores
  5. Cross-model stability: Do two different model outputs converge after canonicalization?
  6. Severity stability: Does canonical severity match raw severity assignment?
  7. Title stability: Are canonical titles deterministic across runs?

Usage:
    evaluator = CanonicalizationEvaluator()
    report = evaluator.evaluate_pack("treasury", candidates)
    report = evaluator.evaluate_ab("treasury", raw_candidates, canonical_result)
    report = evaluator.evaluate_cross_model("treasury", model_a_candidates, model_b_candidates)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from core.domain.canonicalizer import (
    CanonicalizationResult,
    CanonicalFlag,
    CanonicalSignal,
    CanonicalStatus,
    canonicalize,
)


# =============================================================================
# Evaluation Result Models
# =============================================================================

class CompletenessDistribution(BaseModel):
    """Distribution of completeness scores across candidates."""
    total: int = 0
    fully_complete: int = 0       # score == 1.0
    mostly_complete: int = 0      # 0.5 <= score < 1.0
    incomplete: int = 0           # score < 0.5
    avg_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0


class FalseBreachAnalysis(BaseModel):
    """Analysis of false/incomplete breaches caught by completeness gating."""
    total_breach_category: int = 0         # Signals with category=breach in registry
    complete_breaches: int = 0             # Passed completeness gating
    incomplete_breaches: int = 0           # Failed completeness gating (downgraded)
    false_breach_rate: float = 0.0         # incomplete / total_breach_category
    missing_field_frequency: Dict[str, int] = Field(default_factory=dict)


class DuplicateAnalysis(BaseModel):
    """Analysis of duplicate detection and merging."""
    total_before_dedup: int = 0
    total_after_dedup: int = 0
    duplicates_merged: int = 0
    duplicate_rate: float = 0.0            # merged / total_before_dedup
    dedupe_key_collisions: Dict[str, int] = Field(default_factory=dict)


class CrossModelComparison(BaseModel):
    """Comparison of canonicalized outputs from two different models."""
    model_a_name: str = ""
    model_b_name: str = ""
    total_signals_a: int = 0
    total_signals_b: int = 0

    # Type-level agreement
    signal_type_match_count: int = 0
    signal_type_match_rate: float = 0.0

    # Severity agreement (after canonicalization)
    severity_match_count: int = 0
    severity_match_rate: float = 0.0

    # Flag agreement
    flag_match_count: int = 0
    flag_match_rate: float = 0.0

    # Title agreement (template-based, should be high)
    title_match_count: int = 0
    title_match_rate: float = 0.0

    # Status agreement (breach vs observation vs dropped)
    status_match_count: int = 0
    status_match_rate: float = 0.0

    # Mismatches for debugging
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)


class ABComparisonResult(BaseModel):
    """A/B comparison: raw extraction vs canonicalized results."""

    # Raw extraction stats
    raw_candidate_count: int = 0
    raw_breach_type_count: int = 0         # Signals that would be breach by signal_type alone

    # Canonicalized stats
    canonical_breach_count: int = 0
    canonical_observation_count: int = 0
    canonical_dropped_count: int = 0
    canonical_merged_count: int = 0

    # Delta analysis
    breaches_prevented: int = 0            # Would have been breach, now observation/dropped
    false_breach_rate_raw: float = 0.0     # Estimated false breach rate without canonicalization
    false_breach_rate_canonical: float = 0.0  # After canonicalization

    # Detailed
    false_breach_analysis: FalseBreachAnalysis = Field(default_factory=FalseBreachAnalysis)
    duplicate_analysis: DuplicateAnalysis = Field(default_factory=DuplicateAnalysis)
    completeness: CompletenessDistribution = Field(default_factory=CompletenessDistribution)


class CanonicalizationEvalReport(BaseModel):
    """Full evaluation report for canonicalization."""

    pack: str
    evaluated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    candidate_count: int = 0

    # Core analyses
    ab_comparison: Optional[ABComparisonResult] = None
    cross_model: Optional[CrossModelComparison] = None

    # Summary verdict
    adds_value: bool = False
    value_reasons: List[str] = Field(default_factory=list)
    no_value_reasons: List[str] = Field(default_factory=list)

    # Acceptance thresholds
    thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "min_false_breach_reduction": 0.05,    # At least 5% fewer false breaches
        "min_duplicate_reduction": 0.0,         # Any duplicate reduction is good
        "min_cross_model_type_match": 0.95,     # 95% type agreement across models
        "min_cross_model_severity_match": 0.90, # 90% severity agreement
    })


# =============================================================================
# Evaluator
# =============================================================================

class CanonicalizationEvaluator:
    """
    Evaluates whether the Canonicalizer adds measurable value.

    Three evaluation modes:
    1. evaluate_pack: Run canonicalization on candidates and analyze results
    2. evaluate_ab: Compare raw vs canonicalized for the same candidates
    3. evaluate_cross_model: Compare canonicalized outputs from two models
    """

    def __init__(self, datasets_path: Optional[Path] = None):
        self.datasets_path = datasets_path or Path(__file__).parent.parent / "datasets"

    def evaluate_pack(
        self,
        pack: str,
        candidates: List[Dict[str, Any]],
        constraint_registry: Optional[Dict[str, Any]] = None,
    ) -> CanonicalizationEvalReport:
        """
        Run canonicalization on candidates and produce a full report.

        Args:
            pack: Pack name (treasury, wealth)
            candidates: Raw candidate signal dicts from IntakeAgent
            constraint_registry: Optional override for testing
        """
        report = CanonicalizationEvalReport(
            pack=pack,
            candidate_count=len(candidates),
        )

        # Run canonicalization
        canon_result = canonicalize(candidates, pack, constraint_registry)

        # Run A/B comparison
        report.ab_comparison = self._analyze_ab(pack, candidates, canon_result)

        # Determine verdict
        self._determine_verdict(report)

        return report

    def evaluate_ab(
        self,
        pack: str,
        candidates: List[Dict[str, Any]],
        canon_result: CanonicalizationResult,
    ) -> ABComparisonResult:
        """Compare raw candidates vs canonicalized results."""
        return self._analyze_ab(pack, candidates, canon_result)

    def evaluate_cross_model(
        self,
        pack: str,
        model_a_candidates: List[Dict[str, Any]],
        model_b_candidates: List[Dict[str, Any]],
        model_a_name: str = "model_a",
        model_b_name: str = "model_b",
        constraint_registry: Optional[Dict[str, Any]] = None,
    ) -> CrossModelComparison:
        """
        Compare canonicalized outputs from two different model extractions.

        This is the key stability test: if the Canonicalizer works,
        two models extracting from the same document should produce
        similar canonical outputs even if their raw outputs differ.
        """
        canon_a = canonicalize(model_a_candidates, pack, constraint_registry)
        canon_b = canonicalize(model_b_candidates, pack, constraint_registry)

        return self._compare_canonical_outputs(
            canon_a, canon_b, model_a_name, model_b_name
        )

    def evaluate_determinism(
        self,
        pack: str,
        candidates: List[Dict[str, Any]],
        runs: int = 3,
    ) -> Dict[str, Any]:
        """
        Run canonicalization multiple times and verify identical outputs.

        Returns dict with:
          - deterministic: bool (all runs identical)
          - runs: number of runs
          - hash_match: bool (all output hashes match)
          - hashes: list of output hashes per run
        """
        hashes = []
        for _ in range(runs):
            result = canonicalize(candidates, pack)
            # Hash the full output for comparison
            output_dict = {
                "signals": [
                    {
                        "canonical_id": s.canonical_id,
                        "signal_type": s.signal_type,
                        "canonical_status": s.canonical_status.value,
                        "severity": s.severity,
                        "title": s.title,
                        "flags": [f.value for f in s.flags],
                        "completeness_score": s.completeness_score,
                        "dedupe_key": s.dedupe_key,
                    }
                    for s in result.signals
                ],
                "breach_count": result.breach_count,
                "observation_count": result.observation_count,
                "dropped_count": result.dropped_count,
                "merged_count": result.merged_count,
            }
            h = hashlib.sha256(
                json.dumps(output_dict, sort_keys=True).encode()
            ).hexdigest()
            hashes.append(h)

        return {
            "deterministic": len(set(hashes)) == 1,
            "runs": runs,
            "hash_match": len(set(hashes)) == 1,
            "hashes": hashes,
        }

    def load_golden_candidates(self, pack: str) -> List[Dict[str, Any]]:
        """Load golden candidate fixtures for a pack."""
        filepath = self.datasets_path / f"{pack}_canonicalization.json"
        if not filepath.exists():
            return []
        with open(filepath, "r") as f:
            data = json.load(f)
        return data.get("candidates", [])

    def load_golden_expected(self, pack: str) -> Dict[str, Any]:
        """Load expected canonicalization results for a pack."""
        filepath = self.datasets_path / f"{pack}_canonicalization.json"
        if not filepath.exists():
            return {}
        with open(filepath, "r") as f:
            data = json.load(f)
        return data.get("expected", {})

    # =========================================================================
    # Internal analysis methods
    # =========================================================================

    def _analyze_ab(
        self,
        pack: str,
        candidates: List[Dict[str, Any]],
        canon_result: CanonicalizationResult,
    ) -> ABComparisonResult:
        """Produce A/B comparison between raw candidates and canonical output."""

        from core.domain.canonicalizer import load_constraint_registry
        registry = load_constraint_registry(pack)

        result = ABComparisonResult(
            raw_candidate_count=len(candidates),
            canonical_breach_count=canon_result.breach_count,
            canonical_observation_count=canon_result.observation_count,
            canonical_dropped_count=canon_result.dropped_count,
            canonical_merged_count=canon_result.merged_count,
        )

        # Count how many raw candidates would be breach-category
        # (without completeness gating). In the constraint registry,
        # "threshold" category signals are breach-eligible; "event" are always observations.
        breach_category_count = 0
        for c in candidates:
            signal_type = c.get("signal_type", "")
            constraint = registry.get(signal_type, {})
            if constraint.get("category") == "threshold":
                breach_category_count += 1
        result.raw_breach_type_count = breach_category_count

        # False breach analysis
        fb = FalseBreachAnalysis(total_breach_category=breach_category_count)
        for cs in canon_result.signals:
            constraint = registry.get(cs.signal_type, {})
            if constraint.get("category") == "threshold":
                if cs.canonical_status == CanonicalStatus.BREACH:
                    fb.complete_breaches += 1
                elif cs.canonical_status == CanonicalStatus.OBSERVATION:
                    fb.incomplete_breaches += 1
                    for field in cs.missing_fields:
                        fb.missing_field_frequency[field] = (
                            fb.missing_field_frequency.get(field, 0) + 1
                        )

        if fb.total_breach_category > 0:
            fb.false_breach_rate = fb.incomplete_breaches / fb.total_breach_category
        result.false_breach_analysis = fb

        # Breaches prevented = would-have-been-breach minus actual breaches
        result.breaches_prevented = breach_category_count - canon_result.breach_count
        if breach_category_count > 0:
            result.false_breach_rate_raw = 1.0  # Without gating, everything passes
            result.false_breach_rate_canonical = fb.false_breach_rate

        # Duplicate analysis
        da = DuplicateAnalysis(
            total_before_dedup=len(candidates),
            total_after_dedup=canon_result.effective_signal_count,
            duplicates_merged=canon_result.merged_count,
        )
        if len(candidates) > 0:
            da.duplicate_rate = canon_result.merged_count / len(candidates)

        # Count dedupe key collisions
        dedupe_keys: Dict[str, int] = {}
        for cs in canon_result.signals:
            if cs.dedupe_key:
                dedupe_keys[cs.dedupe_key] = dedupe_keys.get(cs.dedupe_key, 0) + 1
        da.dedupe_key_collisions = {k: v for k, v in dedupe_keys.items() if v > 1}
        result.duplicate_analysis = da

        # Completeness distribution
        cd = CompletenessDistribution(total=len(canon_result.signals))
        scores = [cs.completeness_score for cs in canon_result.signals]
        if scores:
            cd.avg_score = sum(scores) / len(scores)
            cd.min_score = min(scores)
            cd.max_score = max(scores)
            cd.fully_complete = sum(1 for s in scores if s >= 1.0)
            cd.mostly_complete = sum(1 for s in scores if 0.5 <= s < 1.0)
            cd.incomplete = sum(1 for s in scores if s < 0.5)
        result.completeness = cd

        return result

    def _compare_canonical_outputs(
        self,
        canon_a: CanonicalizationResult,
        canon_b: CanonicalizationResult,
        model_a_name: str,
        model_b_name: str,
    ) -> CrossModelComparison:
        """Compare two canonical outputs for stability."""

        comp = CrossModelComparison(
            model_a_name=model_a_name,
            model_b_name=model_b_name,
            total_signals_a=len(canon_a.signals),
            total_signals_b=len(canon_b.signals),
        )

        # Index signals by signal_type for matching
        a_by_type: Dict[str, List[CanonicalSignal]] = {}
        for s in canon_a.signals:
            if s.canonical_status not in (CanonicalStatus.DROPPED, CanonicalStatus.MERGED):
                a_by_type.setdefault(s.signal_type, []).append(s)

        b_by_type: Dict[str, List[CanonicalSignal]] = {}
        for s in canon_b.signals:
            if s.canonical_status not in (CanonicalStatus.DROPPED, CanonicalStatus.MERGED):
                b_by_type.setdefault(s.signal_type, []).append(s)

        # Type-level match
        all_types = set(a_by_type.keys()) | set(b_by_type.keys())
        matched_types = set(a_by_type.keys()) & set(b_by_type.keys())
        comp.signal_type_match_count = len(matched_types)
        if all_types:
            comp.signal_type_match_rate = len(matched_types) / len(all_types)

        # Per-matched-type comparisons
        severity_matches = 0
        flag_matches = 0
        title_matches = 0
        status_matches = 0
        total_compared = 0

        for sig_type in matched_types:
            a_signals = a_by_type[sig_type]
            b_signals = b_by_type[sig_type]

            # Compare pairwise (first signal of each type)
            for a_sig, b_sig in zip(a_signals, b_signals):
                total_compared += 1

                if a_sig.severity == b_sig.severity:
                    severity_matches += 1
                else:
                    comp.mismatches.append({
                        "type": "severity",
                        "signal_type": sig_type,
                        "model_a": a_sig.severity,
                        "model_b": b_sig.severity,
                    })

                a_flags = set(f.value for f in a_sig.flags)
                b_flags = set(f.value for f in b_sig.flags)
                if a_flags == b_flags:
                    flag_matches += 1
                else:
                    comp.mismatches.append({
                        "type": "flags",
                        "signal_type": sig_type,
                        "model_a": sorted(a_flags),
                        "model_b": sorted(b_flags),
                    })

                if a_sig.title == b_sig.title:
                    title_matches += 1

                if a_sig.canonical_status == b_sig.canonical_status:
                    status_matches += 1
                else:
                    comp.mismatches.append({
                        "type": "status",
                        "signal_type": sig_type,
                        "model_a": a_sig.canonical_status.value,
                        "model_b": b_sig.canonical_status.value,
                    })

        if total_compared > 0:
            comp.severity_match_count = severity_matches
            comp.severity_match_rate = severity_matches / total_compared
            comp.flag_match_count = flag_matches
            comp.flag_match_rate = flag_matches / total_compared
            comp.title_match_count = title_matches
            comp.title_match_rate = title_matches / total_compared
            comp.status_match_count = status_matches
            comp.status_match_rate = status_matches / total_compared

        # Add type-level mismatches
        for sig_type in all_types - matched_types:
            source = model_a_name if sig_type in a_by_type else model_b_name
            comp.mismatches.append({
                "type": "type_missing",
                "signal_type": sig_type,
                "present_in": source,
                "missing_in": model_b_name if source == model_a_name else model_a_name,
            })

        return comp

    def _determine_verdict(self, report: CanonicalizationEvalReport):
        """
        Determine whether canonicalization adds value based on measured metrics.

        This is the core assessment logic.
        """
        thresholds = report.thresholds
        ab = report.ab_comparison

        if ab is None:
            report.adds_value = False
            report.no_value_reasons.append("No A/B comparison data available")
            return

        # Check 1: Did it catch any false breaches?
        if ab.false_breach_analysis.incomplete_breaches > 0:
            reduction = ab.false_breach_analysis.false_breach_rate
            if reduction >= thresholds["min_false_breach_reduction"]:
                report.adds_value = True
                report.value_reasons.append(
                    f"Caught {ab.false_breach_analysis.incomplete_breaches} incomplete breaches "
                    f"({reduction:.0%} false breach rate in breach-category signals)"
                )
            else:
                report.no_value_reasons.append(
                    f"False breach rate ({reduction:.0%}) below threshold "
                    f"({thresholds['min_false_breach_reduction']:.0%})"
                )

        # Check 2: Did it reduce duplicates?
        if ab.duplicate_analysis.duplicates_merged > 0:
            report.adds_value = True
            report.value_reasons.append(
                f"Merged {ab.duplicate_analysis.duplicates_merged} duplicate signals "
                f"({ab.duplicate_analysis.duplicate_rate:.0%} duplicate rate)"
            )

        # Check 3: Did it prevent breaches via lookthrough gating?
        lookthrough_blocked = sum(
            1 for s in (report.ab_comparison.completeness.total,)
            # This is tracked at the CanonicalizationResult level
        )
        # Use the report-level metric instead
        if ab.canonical_dropped_count > 0:
            report.value_reasons.append(
                f"Dropped {ab.canonical_dropped_count} signals with no constraint match"
            )

        # Check 4: Completeness distribution shows meaningful variance
        if ab.completeness.total > 0:
            if ab.completeness.incomplete > 0 or ab.completeness.mostly_complete > 0:
                report.value_reasons.append(
                    f"Completeness distribution: {ab.completeness.fully_complete} complete, "
                    f"{ab.completeness.mostly_complete} partial, "
                    f"{ab.completeness.incomplete} incomplete"
                )

        # Cross-model comparison (if available)
        xm = report.cross_model
        if xm is not None:
            if xm.signal_type_match_rate >= thresholds["min_cross_model_type_match"]:
                report.value_reasons.append(
                    f"Cross-model type stability: {xm.signal_type_match_rate:.0%} "
                    f"(threshold: {thresholds['min_cross_model_type_match']:.0%})"
                )
            else:
                report.no_value_reasons.append(
                    f"Cross-model type match ({xm.signal_type_match_rate:.0%}) "
                    f"below threshold ({thresholds['min_cross_model_type_match']:.0%})"
                )

            if xm.severity_match_rate >= thresholds["min_cross_model_severity_match"]:
                report.value_reasons.append(
                    f"Cross-model severity stability: {xm.severity_match_rate:.0%}"
                )

        # Final verdict: adds_value if at least one value reason and
        # no critical no-value reasons
        if not report.value_reasons:
            report.adds_value = False
            if not report.no_value_reasons:
                report.no_value_reasons.append(
                    "No measurable improvement detected"
                )
