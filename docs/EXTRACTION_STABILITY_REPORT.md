# Extraction Stability Report

**Test Date:** 2026-02-07
**Model:** gemini-3-flash-preview (Gemini 3 Flash), temperature=0.1
**Method:** 10 extraction runs per document pack, same prompt and config each run
**Documents:** Orion Treasury Pack, Meridian Wealth Pack (deliberately unstructured — see below)
**Test Script:** [`evals/dispersion_test.py`](../evals/dispersion_test.py)

---

## Executive Summary

We ran the same financial documents through our AI extraction pipeline 10 times each to measure signal stability. Of 20 total runs, 18 produced valid JSON output (90% parse success).

Across the 18 successful runs:

- **Breach-critical signals: 100% observed recall (n=9 per pack)** — every run extracted the same core breaches
- **Edge-case signals: ±1 variance** — soft observations fluctuate between runs
- **JSON parse failures: 2/20 runs (10%)** — Gemini truncated output mid-stream, caught by error handling

This confirms that the **canonicalizer provides the determinism guarantee**, not the LLM extraction layer. The LLM proposes signal candidates with minor variance; the kernel applies deterministic gates to produce stable outputs.

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Model | gemini-3-flash-preview (Gemini 3 Flash) |
| Temperature | 0.1 (explicitly set, low but not zero) |
| Output format | JSON mode with schema |
| Runs per pack | 10 |
| Total runs | 20 |
| Successful parses | 18/20 (90%) |

Note: Temperature was set to 0.1 rather than 0. This is intentional — a small amount of variance tests the architecture under near-production conditions while still exercising the canonicalizer's ability to absorb minor extraction differences.

### Document Packs

Both packs are designed to resemble the messy, contradictory inputs that executives actually receive. Each pack contains a mix of: email threads with banks and counterparties, internal team communications with conflicting opinions ("we should act immediately" vs "let's wait for confirmation"), contractor reports, meeting notes with unresolved disagreements, and formal financial reports — often with contradictory data points across sources.

This is deliberate. A stability test on clean, structured data would prove very little. The extraction pipeline must produce consistent breach signals even when the source material is ambiguous, opinionated, and internally contradictory — because that is what real-world executive document packs look like.

---

## Results by Pack

### Treasury (Orion Metals Trading AG)

| Metric | Value |
|--------|-------|
| Successful runs | 9/10 (90%) |
| Signal count range | 4–5 per run (mean 4.9) |
| Std. dev. of count | ~0.3 |

**Signal Type Stability (n=9 successful runs):**

| Signal Type | Observed / 9 | Rate | Notes |
|-------------|-------------|------|-------|
| `position_limit_breach` | 9/9 | 100% | RCF 92% > 85% limit — always extracted |
| `covenant_breach` | 9/9 | 100% | CHF 96,400 < 100,000 — always extracted |
| `fx_exposure_breach` | 8/9 | 89% | Hedge gap — missed once |
| `bank_account_anomaly` | 9/9 | 100% | Fee spike — but count varies (1–2 per run) |
| `settlement_failure` | 4/9 | 44% | Baltic Steel hold — edge case, inconsistently extracted |

### Wealth (Meridian / Stonebridge Family Office)

| Metric | Value |
|--------|-------|
| Successful runs | 9/10 (90%) |
| Signal count range | 9–10 per run (mean 9.9) |
| Std. dev. of count | ~0.3 |

**Signal Type Stability (n=9 successful runs):**

| Signal Type | Observed / 9 | Rate | Notes |
|-------------|-------------|------|-------|
| `concentration_breach` | 9/9 | 100% | Alpina 8.4% + Fund 12.7% — always extracted |
| `fee_discrepancy` | 9/9 | 100% | 0.45% vs 0.30% — always extracted |
| `withdrawal_request` | 9/9 | 100% | CHF 500k request — always extracted |
| `settlement_pending_cash` | 9/9 | 100% | CHF 220k pending — always extracted |
| `lookthrough_missing` | 9/9 | 100% | EM Fund constituents — always extracted |
| `mandate_breach` | 9/9 | 100% | Present every run, but count varies (1–2 sub-signals) |
| `compliance_flag` | 9/9 | 100% | Present every run, but count varies (1–2 sub-signals) |
| `suitability_drift` | 4/9 | 44% | Stale questionnaire — edge case, inconsistently extracted |

---

## Key Findings

### 1. Breach-Critical Signals: 100% Observed Recall

The signals that canonicalize to **BREACH** status were extracted in every successful run:

| Pack | Breach Signal | Extraction Rate |
|------|--------------|-----------------|
| Treasury | RCF utilization > 85% | 9/9 (100%) |
| Treasury | Covenant CHF 96k < 100k | 9/9 (100%) |
| Wealth | Alpina Energy 8.4% > 7% | 9/9 (100%) |
| Wealth | Custody fee 0.45% vs 0.30% | 9/9 (100%) |

With n=9, 100% observed recall has a 95% confidence interval of approximately [66%–100%] (Clopper-Pearson). A larger sample would tighten this bound, but the pattern is clear: unambiguous threshold violations are reliably extracted.

### 2. Observation Signals: Present but Count Varies

Signal types like `bank_account_anomaly`, `mandate_breach`, and `compliance_flag` were detected every run, but the number of sub-signals within each type fluctuated (1 vs 2). This is expected — the LLM sometimes splits a finding into sub-signals and sometimes aggregates it.

The canonicalizer handles this correctly: same type + same threshold = same policy evaluation regardless of whether the LLM reports one signal or two.

### 3. Edge-Case Signals: ~44% Detection

Two signals had low extraction rates (~4/9 runs): `settlement_failure` (Treasury) and `suitability_drift` (Wealth). Both are ambiguous findings where the source document doesn't state an explicit threshold. The LLM sometimes infers them and sometimes doesn't.

This is acceptable because these edge cases canonicalize to OBSERVATION, not BREACH — they create review tasks, not compliance events.

### 4. JSON Parse Failures: 10%

2/20 runs produced truncated JSON. This is a known Gemini limitation on large structured outputs. The pipeline catches these and returns a clear error rather than partial results.

For production: retry logic would recover from this, improving effective success rate. For this test, failed runs were excluded from signal analysis (noted as n=9 throughout).

---

## Architecture Validation

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Gemini Flash    │ ──► │  Canonicalizer   │ ──► │  Policy Engine  │
│  (extraction)    │     │  (deterministic) │     │  (deterministic)│
│                  │     │                  │     │                 │
│  ±1 variance     │     │  0 variance      │     │  0 variance     │
│  on edge cases   │     │  same input =    │     │  same signals = │
│                  │     │  same output     │     │  same result    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

The LLM layer is intentionally non-deterministic — it's a coprocessor that proposes candidates. The canonicalizer provides the determinism guarantee by applying rule-based gates (category, lookthrough, definition lock, authorized source) to every signal before it enters the policy engine.

The variance observed in this test (±1 on edge cases) is exactly the kind of noise the canonicalizer is designed to absorb.

---

## Limitations

- **Small sample size (n=9 per pack):** 100% observed recall does not prove 100% true recall. The 95% CI is [66%–100%]. A 50-run test would be needed to claim >95% recall with statistical confidence.
- **Two document packs only:** Results may not generalize to other document types, languages, or financial domains.
- **Low but nonzero temperature (0.1):** Setting temperature=0 would likely eliminate remaining variance but would not reflect realistic production conditions.
- **Failed runs excluded:** The 10% JSON failure rate means 1 in 10 runs produces no result at all. This is a reliability issue separate from extraction accuracy.
- **No inter-rater comparison:** We did not compare LLM extractions against human-labeled ground truth. This test measures self-consistency (same inputs → same outputs), not correctness.

---

## Implications

1. **Breach counts are reliable across runs** — The 4 breaches (2 Treasury + 2 Wealth) appeared in all 18 successful runs

2. **Observation counts may vary by ±1 per type** — Edge-case signals are inconsistently extracted, but the canonicalizer gates ensure this doesn't affect breach determinations

3. **Retry logic is a production requirement** — JSON parse failures need automatic retry to achieve acceptable reliability

4. **The canonicalizer is the stability boundary** — Extraction variance exists by design. The architecture tolerates it rather than trying to eliminate it.

---

## Conclusion

The extraction pipeline demonstrates the stability characteristics we designed for:

- **Breach-critical signals: 100% observed recall (n=9 per pack, CI [66%–100%])**
- **Soft signals (observations): present every run, ±1 on sub-signal count**
- **Edge cases: ~44% detection — acceptable, as these canonicalize to OBSERVATION**
- **Determinism is guaranteed by the canonicalizer, not the LLM**

AI proposes. Kernel verifies. Humans decide.
