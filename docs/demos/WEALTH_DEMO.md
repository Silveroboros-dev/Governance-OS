# Wealth Management Pack Demo Script

**Duration:** 15-20 minutes
**Prerequisites:** Docker Desktop running, no prior database state required

This script demonstrates the complete governance loop for Wealth Management:
`Signal → Policy Evaluation → Exception → Decision → Evidence Pack`

Focus areas: Suitability, Portfolio Drift, Concentration Risk, Tax Optimization

---

## 1. Environment Setup

### Start the System

```bash
# From project root
cd /path/to/Governance-OS

# Start all services
docker compose up -d

# Verify services are healthy
docker compose ps
```

### Access Points
- **UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

---

## 2. Seed Wealth Management Data

### Load Policies and Demo Signals

```bash
# Seed Wealth policies + scenario data
docker compose exec backend python -m core.scripts.seed_fixtures --pack=wealth --scenarios
```

This will:
1. Create Wealth policies (Suitability, Drift, Concentration, Tax, etc.)
2. Load demo signals from `packs/wealth/fixtures/scenarios.json`
3. Automatically trigger evaluations to generate exceptions

Expected output:
```
Seeding wealth policies...
  Created policy: Suitability Check Policy
  Created policy: Portfolio Drift Policy
  Created policy: Concentration Limit Policy
  Created policy: Tax Loss Harvest Policy
  ...

Loading wealth scenarios from fixtures...
  Scenario: Suitability Mismatch - Conservative Client
    Created signal: suitability_mismatch
  Scenario: Equity Allocation Drift - HNWI Client
    Created signal: portfolio_drift
  ...

Triggering evaluations to generate exceptions...
  WEALTH: Evaluating policies against signals
    Exception raised: Suitability mismatch detected (critical)
    Exception raised: Portfolio drift exceeds threshold (high)
    ...
```

---

## 3. Key Wealth Management Scenarios

### Scenario Overview

| ID | Scenario | Severity | Key Issue |
|----|----------|----------|-----------|
| `suitability_mismatch_aggressive` | Retiree + Tech Inheritance | Critical | Risk score 3 vs portfolio risk 7 |
| `portfolio_drift_equities_high` | HNWI Equity Drift | High | 72% equities vs 60% target |
| `concentration_breach_executive` | Executive Apple Stock | Critical | 28% concentration vs 10% limit |
| `tax_loss_harvest_tech` | META Loss Opportunity | High | $140K loss, $56K tax savings |
| `large_withdrawal_request` | $2M Property Purchase | Critical | 40% withdrawal, liquidation needed |
| `correlation_spike_crisis` | Diversification Breakdown | High | Correlation spike 0.72 → 0.94 |
| `fee_increase_notification` | Management Fee Increase | High | 75 bps → 100 bps, consent required |

---

## 4. Demo Flow: Suitability Mismatch (Recommended Start)

### The Story

*A conservative retiree (Mrs. Johnson, risk score 3) inherited concentrated tech positions from her late husband. Her portfolio risk score is now 7, significantly exceeding suitability thresholds.*

### Step 1: View Exception Timeline

1. Open http://localhost:3000
2. Select **"Wealth"** from pack selector
3. Navigate to **Exceptions**
4. Find **"Suitability mismatch detected"** (Critical severity)

### Step 2: Open Decision UI

Click on the exception to see the one-screen decision interface:

**Left Column - Context:**
- Impacted Policy: "Suitability Check Policy"
- What Changed:
  - Client risk score: 3 (conservative)
  - Portfolio risk score: 7 (aggressive)
  - Risk delta: 4 points
  - Top contributors: NVDA (15%), TSLA (8%), ARKK (5%)
- Uncertainty: Last profile update was 2025-06-15

**Center Column - Options:**
- **Rebalance to Target Risk** - Liquidate high-risk positions to match profile
- **Update Client Risk Profile** - Reassess if client's circumstances have changed
- **Staged Rebalancing Plan** - Gradual transition over 3-6 months
- **Document Exception** - Client-approved deviation with enhanced monitoring

**Right Column - Decision:**
- Select: "Staged Rebalancing Plan"
- Rationale: "Client is emotionally attached to inherited positions. Recommend staged liquidation over 6 months to reduce portfolio risk score to 4-5, with quarterly reviews. Tax implications to be discussed with client's CPA."

### Step 3: Commit Decision

Click "Commit Decision" to:
1. Record the decision immutably
2. Mark exception as resolved
3. Generate evidence pack
4. Navigate to trace view

---

## 5. Demo Flow: Executive Concentration Risk

### The Story

*Mr. Chen, a senior Apple executive, has seen his company stock appreciation push concentration to 28% of his $10M portfolio, breaching the 10% limit. As a restricted insider, this position requires careful handling.*

### Key Details in Decision UI

**Context:**
- Security: Apple Inc. (AAPL)
- Current weight: 28%
- Limit: 10%
- Position value: $2.8M
- Restricted security: Yes (insider status)

**Options:**
- Systematic Liquidation (10b5-1 Plan)
- Exchange Fund Contribution
- Hedging Strategy (Collars/Puts)
- Document Client Election

**Sample Rationale:**
"Recommend 10b5-1 plan to systematically reduce Apple concentration over 12 months. Plan should be established during open trading window and filed with compliance. Target: 15% concentration by EOY with continued monitoring."

---

## 6. Demo Flow: Large Withdrawal Request

### The Story

*The Martinez family is purchasing a $2M vacation home. This requires liquidating 40% of their $5M portfolio. Only $150K cash is available.*

### Key Details in Decision UI

**Context:**
- Withdrawal amount: $2,000,000 (40%)
- Available cash: $150,000
- Liquidation required: $1,850,000
- Target date: February 15, 2026

**Options:**
- Execute Full Liquidation
- Suggest Partial Financing
- Request Delay for Tax Planning
- Staged Liquidation Schedule

**Sample Rationale:**
"Given 4-week runway to Feb 15, recommend staged liquidation prioritizing: (1) positions with losses for tax harvesting, (2) overweight positions, (3) lower conviction holdings. Preserve core equity positions and maintain emergency reserve."

---

## 7. View Evidence Pack

After making a decision, the trace view shows:

**Visual Chain:**
```
Signal → Evaluation → Exception → Decision → Evidence
```

**Evidence Pack Contains:**
- Full decision record (option, rationale, timestamp, user)
- Exception context (severity, client ID, portfolio ID)
- Original signal data (suitability scores, holdings breakdown)
- Policy version that triggered the exception
- SHA-256 content hash for integrity verification

### Export Evidence

```bash
# Get decision ID from URL
DECISION_ID="<your-decision-id>"

# Export for compliance records
curl "http://localhost:8000/api/v1/evidence/${DECISION_ID}/export?format=json" \
  -o suitability-evidence.json
```

---

## 8. Dashboard & KPI Snapshot

### Check Stats via API

```bash
curl "http://localhost:8000/api/v1/stats?pack=wealth" | python -m json.tool
```

Response:
```json
{
  "pack": "wealth",
  "exceptions": {
    "open": 5,
    "by_severity": {
      "critical": 3,
      "high": 2,
      "medium": 0,
      "low": 0
    }
  },
  "decisions": {
    "total": 2,
    "last_24h": 2
  },
  "signals": {
    "total": 7,
    "last_24h": 7
  },
  "policies": {
    "total": 7,
    "active": 7
  }
}
```

### KPIs for Wealth Management

- **Suitability exceptions open:** Critical metric for compliance
- **Concentration breaches:** Number of clients over limits
- **Decisions made today:** Advisor productivity
- **Average time-to-resolution:** (Future metric)

---

## 9. Compliance Use Cases

### Regulatory Examination Scenario

*"Show me all suitability decisions for Q4 2025"*

```bash
# Query decisions by date range
curl "http://localhost:8000/api/v1/decisions?pack=wealth&from_date=2025-10-01&to_date=2025-12-31" \
  | python -m json.tool
```

### Client Complaint Investigation

*"Why did we rebalance Mrs. Johnson's portfolio?"*

1. Navigate to Decisions page
2. Search by client ID or exception title
3. Click decision to view full trace
4. Export evidence pack for documentation

### Audit Trail Verification

Every evidence pack includes:
- Content hash (SHA-256) for integrity
- Timestamp of decision
- User who made decision
- Complete signal → decision chain

---

## 10. API Walkthrough (For Integration Demo)

### List Open Exceptions

```bash
curl "http://localhost:8000/api/v1/exceptions?pack=wealth&status=open" | python -m json.tool
```

### Get Exception Details

```bash
curl "http://localhost:8000/api/v1/exceptions/{exception_id}" | python -m json.tool
```

Returns full context including:
- Evaluation summary
- Policy that triggered it
- All contributing signals

### Create Decision

```bash
curl -X POST "http://localhost:8000/api/v1/decisions" \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "...",
    "chosen_option_id": "staged_rebalancing",
    "rationale": "Gradual transition plan approved by client",
    "decided_by": "advisor@wealth.com"
  }'
```

### Get Evidence Pack

```bash
curl "http://localhost:8000/api/v1/evidence/{decision_id}" | python -m json.tool
```

---

## 11. Demonstrating Governance Principles

### No Recommendations

Point out to audience:
- All options are presented equally
- No "recommended" or "suggested" labels
- Human judgment is required for suitability decisions

### Uncertainty is Visible

Show in decision UI:
- Signal reliability indicators
- Last profile update date
- Confidence gaps flagged explicitly

### One-Screen Commitment

Demonstrate:
- All context visible without scrolling
- Three-column layout: Context | Options | Decision
- No drilldowns required for basic decisions

### Evidence Trail

Show evidence pack includes:
- Every signal that contributed
- Policy version at time of evaluation
- Complete decision rationale
- Cryptographic hash for integrity

---

## 12. Cleanup

### Reset for Fresh Demo

```bash
# Full reset
docker compose down -v
docker compose up -d
docker compose exec backend python -m core.scripts.seed_fixtures --pack=wealth --scenarios
```

### Switch Between Packs

The pack selector in the UI allows switching between Treasury and Wealth:
- Each pack has isolated data
- Policies and signal types are pack-specific
- Stats and exceptions filter by selected pack

---

## Key Differentiators for Wealth Management

1. **Suitability Compliance:** Automated detection of client/portfolio mismatches
2. **Fiduciary Documentation:** Every recommendation has an evidence trail
3. **Tax-Aware Decisions:** Tax implications visible in decision context
4. **Regulatory Ready:** Evidence packs designed for examination
5. **Client-Centric:** Context includes client profile, portfolio details, restrictions

---

## Troubleshooting

### No wealth exceptions showing

```bash
# Ensure wealth scenarios are loaded
docker compose exec backend python -m core.scripts.seed_fixtures --pack=wealth --scenarios --evaluate
```

### Missing policies

```bash
# Check policies exist
curl "http://localhost:8000/api/v1/policies?pack=wealth" | python -m json.tool
```

### Database connection issues

```bash
# Restart services
docker compose restart backend
docker compose logs backend
```
