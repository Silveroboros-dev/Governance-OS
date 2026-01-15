"""
Extraction Accuracy Evaluator - Sprint 3

Evaluates IntakeAgent extraction against golden datasets.

Metrics:
- Precision: What fraction of extracted signals are correct?
- Recall: What fraction of expected signals were extracted?
- Confidence calibration: Are confidence scores accurate?
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class ExtractionMatch(BaseModel):
    """Match between expected and extracted signal."""
    expected_signal_type: str
    extracted_signal_type: Optional[str]
    matched: bool
    confidence: Optional[float]
    notes: Optional[str]


class ExtractionEvalResult(BaseModel):
    """Result of extraction evaluation."""

    document_id: str
    document_source: str

    # Counts
    expected_count: int
    extracted_count: int
    true_positive: int
    false_positive: int
    false_negative: int

    # Metrics
    precision: float
    recall: float
    f1_score: float

    # Confidence calibration
    avg_confidence_correct: Optional[float]
    avg_confidence_incorrect: Optional[float]
    calibration_error: Optional[float]

    # Details
    matches: List[ExtractionMatch] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ExtractionEvalSummary(BaseModel):
    """Summary of extraction evaluation run."""

    run_id: str = Field(default_factory=lambda: f"extraction_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Aggregate metrics
    total_documents: int = 0
    avg_precision: float = 0.0
    avg_recall: float = 0.0
    avg_f1: float = 0.0
    avg_calibration_error: float = 0.0

    # Thresholds
    precision_threshold: float = 0.85
    recall_threshold: float = 0.80
    calibration_threshold: float = 0.10

    # Results
    results: List[ExtractionEvalResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if evaluation passed all thresholds."""
        return (
            self.avg_precision >= self.precision_threshold
            and self.avg_recall >= self.recall_threshold
            and self.avg_calibration_error <= self.calibration_threshold
        )


class ExtractionEvaluator:
    """
    Evaluates IntakeAgent extraction accuracy.

    Uses golden datasets of documents with expected signals.
    """

    def __init__(
        self,
        datasets_path: Optional[Path] = None,
        precision_threshold: float = 0.85,
        recall_threshold: float = 0.80,
        calibration_threshold: float = 0.10,
    ):
        """
        Initialize evaluator.

        Args:
            datasets_path: Path to datasets directory
            precision_threshold: Minimum precision to pass
            recall_threshold: Minimum recall to pass
            calibration_threshold: Maximum calibration error to pass
        """
        self.datasets_path = datasets_path or Path(__file__).parent.parent / "datasets"
        self.precision_threshold = precision_threshold
        self.recall_threshold = recall_threshold
        self.calibration_threshold = calibration_threshold

    def load_dataset(self, pack: str) -> List[Dict[str, Any]]:
        """Load extraction dataset for a pack."""
        filename = f"{pack}_extraction.json"
        filepath = self.datasets_path / filename

        if not filepath.exists():
            # Return empty dataset if not found
            return []

        with open(filepath, "r") as f:
            data = json.load(f)

        return data.get("documents", [])

    def _match_signals(
        self,
        expected: List[Dict[str, Any]],
        extracted: List[Dict[str, Any]],
    ) -> Tuple[int, int, int, List[ExtractionMatch]]:
        """
        Match expected signals with extracted signals.

        Returns: (true_positive, false_positive, false_negative, matches)
        """
        matches = []
        matched_extracted = set()

        true_positive = 0
        false_negative = 0

        for exp in expected:
            exp_type = exp.get("signal_type")
            exp_payload = exp.get("payload", {})

            # Find matching extraction
            matched = False
            for i, ext in enumerate(extracted):
                if i in matched_extracted:
                    continue

                ext_type = ext.get("signal_type")
                if ext_type == exp_type:
                    # Check payload similarity (simplified - just type match)
                    matched = True
                    matched_extracted.add(i)
                    true_positive += 1

                    matches.append(ExtractionMatch(
                        expected_signal_type=exp_type,
                        extracted_signal_type=ext_type,
                        matched=True,
                        confidence=ext.get("confidence"),
                        notes="Type match"
                    ))
                    break

            if not matched:
                false_negative += 1
                matches.append(ExtractionMatch(
                    expected_signal_type=exp_type,
                    extracted_signal_type=None,
                    matched=False,
                    confidence=None,
                    notes="Not extracted"
                ))

        # Count false positives (extracted but not expected)
        false_positive = len(extracted) - len(matched_extracted)

        for i, ext in enumerate(extracted):
            if i not in matched_extracted:
                matches.append(ExtractionMatch(
                    expected_signal_type="",
                    extracted_signal_type=ext.get("signal_type"),
                    matched=False,
                    confidence=ext.get("confidence"),
                    notes="Unexpected extraction"
                ))

        return true_positive, false_positive, false_negative, matches

    def _calculate_calibration(
        self,
        matches: List[ExtractionMatch],
        extracted: List[Dict[str, Any]],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate confidence calibration metrics.

        Returns: (avg_confidence_correct, avg_confidence_incorrect, calibration_error)
        """
        correct_confidences = []
        incorrect_confidences = []

        for match in matches:
            if match.confidence is not None:
                if match.matched:
                    correct_confidences.append(match.confidence)
                elif match.extracted_signal_type:  # False positive
                    incorrect_confidences.append(match.confidence)

        avg_correct = sum(correct_confidences) / len(correct_confidences) if correct_confidences else None
        avg_incorrect = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else None

        # Calibration error: difference between confidence and actual accuracy
        # For a well-calibrated model, avg confidence should match precision
        if correct_confidences and incorrect_confidences:
            all_confidences = correct_confidences + incorrect_confidences
            avg_confidence = sum(all_confidences) / len(all_confidences)
            actual_accuracy = len(correct_confidences) / len(all_confidences)
            calibration_error = abs(avg_confidence - actual_accuracy)
        else:
            calibration_error = None

        return avg_correct, avg_incorrect, calibration_error

    def evaluate_document(
        self,
        document: Dict[str, Any],
        extracted: List[Dict[str, Any]],
    ) -> ExtractionEvalResult:
        """
        Evaluate extraction for a single document.

        Args:
            document: Document with expected signals
            extracted: Extracted signals from IntakeAgent

        Returns:
            ExtractionEvalResult
        """
        expected = document.get("expected_signals", [])

        # Match signals
        tp, fp, fn, matches = self._match_signals(expected, extracted)

        # Calculate precision and recall
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Calculate calibration
        avg_correct, avg_incorrect, calibration_error = self._calculate_calibration(
            matches, extracted
        )

        return ExtractionEvalResult(
            document_id=document.get("id", "unknown"),
            document_source=document.get("source", ""),
            expected_count=len(expected),
            extracted_count=len(extracted),
            true_positive=tp,
            false_positive=fp,
            false_negative=fn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            avg_confidence_correct=avg_correct,
            avg_confidence_incorrect=avg_incorrect,
            calibration_error=calibration_error,
            matches=matches,
        )

    def evaluate_agent(
        self,
        agent,
        pack: str,
        verbose: bool = False,
    ) -> ExtractionEvalSummary:
        """
        Evaluate an IntakeAgent against the dataset.

        Args:
            agent: IntakeAgent instance
            pack: Pack to evaluate (treasury/wealth)
            verbose: Print detailed output

        Returns:
            ExtractionEvalSummary
        """
        summary = ExtractionEvalSummary(
            precision_threshold=self.precision_threshold,
            recall_threshold=self.recall_threshold,
            calibration_threshold=self.calibration_threshold,
        )

        dataset = self.load_dataset(pack)
        summary.total_documents = len(dataset)

        if verbose:
            print(f"\nEvaluating {len(dataset)} {pack} documents...")
            print("=" * 60)

        precisions = []
        recalls = []
        f1s = []
        calibration_errors = []

        for doc in dataset:
            # Extract signals using agent
            content = doc.get("content", "")
            source = doc.get("source", "unknown")

            try:
                result = agent.extract_signals_sync(
                    content=content,
                    pack=pack,
                    document_source=source,
                )
                extracted = [
                    {
                        "signal_type": c.signal_type,
                        "payload": c.payload,
                        "confidence": c.confidence,
                    }
                    for c in result.candidates
                ]
            except Exception as e:
                if verbose:
                    print(f"[ERROR] {doc.get('id', 'unknown')}: {e}")
                continue

            # Evaluate extraction
            eval_result = self.evaluate_document(doc, extracted)
            summary.results.append(eval_result)

            precisions.append(eval_result.precision)
            recalls.append(eval_result.recall)
            f1s.append(eval_result.f1_score)
            if eval_result.calibration_error is not None:
                calibration_errors.append(eval_result.calibration_error)

            if verbose:
                status = "PASS" if eval_result.precision >= self.precision_threshold else "FAIL"
                print(f"[{status}] {eval_result.document_id}: P={eval_result.precision:.2f} R={eval_result.recall:.2f}")

        # Calculate averages
        summary.avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        summary.avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        summary.avg_f1 = sum(f1s) / len(f1s) if f1s else 0.0
        summary.avg_calibration_error = sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0.0

        summary.completed_at = datetime.utcnow()

        if verbose:
            print("=" * 60)
            print(f"\nResults:")
            print(f"  Precision: {summary.avg_precision:.1%} (threshold: {self.precision_threshold:.0%})")
            print(f"  Recall: {summary.avg_recall:.1%} (threshold: {self.recall_threshold:.0%})")
            print(f"  F1 Score: {summary.avg_f1:.1%}")
            print(f"  Calibration Error: {summary.avg_calibration_error:.2f} (threshold: {self.calibration_threshold:.2f})")
            print(f"\nOverall: {'PASS' if summary.passed else 'FAIL'}")

        return summary
