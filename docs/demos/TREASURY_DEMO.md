# Treasury Pack Demo Script

**Duration:** 15-20 minutes
**Prerequisites:** Docker Desktop running, no prior database state required

This script demonstrates the complete governance loop for Corporate Treasury:
`Signal → Policy Evaluation → Exception → Decision → Evidence Pack`

---

## 1. Environment Setup

### Start the System

```bash
# From project root
cd /path/to/Governance-OS

# Start all services (postgres, backend, frontend)
docker compose up -d

# Verify services are healthy
docker compose ps
```

Expected output:
```
NAME                    STATUS
governance-os-backend   Up (healthy)
governance-os-frontend  Up
governance-os-postgres  Up (healthy)
```

### Access Points
- **UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health

---

## 2. Seed Treasury Data

### Load Policies and Demo Signals

```bash
# Seed Treasury policies + scenario data
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenarios
```

This will:
1. Create Treasury policies (Position Limit, Volatility, Credit Risk, etc.)
2. Load demo signals from `packs/treasury/fixtures/scenarios.json`
3. Automatically trigger evaluations to generate exceptions

Expected output:
```
Seeding treasury policies...
  Created policy: Position Limit Policy
  Created policy: Market Volatility Policy
  Created policy: Credit Risk Policy
  ...

Loading treasury scenarios from fixtures...
  Scenario: Critical BTC Position Limit Breach
    Created signal: position_limit_breach
  ...

Triggering evaluations to generate exceptions...
  TREASURY: Evaluating 6 policies against 7 signals
    Exception raised: BTC position exceeds approved limit (critical)
    Exception raised: ETH volatility exceeds threshold (high)
    ...
```

---

## 3. View Exception Timeline (UI)

### Navigate to Exceptions

1. Open http://localhost:3000
2. Select **"Treasury"** from the pack selector (top-right)
3. Click **"Exceptions"** in the navigation

### Timeline Features to Demonstrate

**Grouping by Date:**
- Exceptions are grouped as "Today", "Yesterday", or by weekday
- Visual timeline with vertical connector line

**Filtering:**
- **Status filter:** All / Open / Resolved / Dismissed
- **Severity filter:** All / Critical / High / Medium / Low

**Quick Stats:**
- Click stat cards to filter (e.g., click "Critical" card to see only critical exceptions)

**Sample Walkthrough:**
```
Filter: Status = Open, Severity = Critical

You should see:
- BTC Position Limit Breach (critical)
- Cash Shortfall (critical)
- Settlement Failure (critical)
```

---

## 4. Make a Decision (One-Screen UI)

### Click on "Critical BTC Position Limit Breach"

The one-screen decision UI has three columns:

**Left Column - Context:**
- Impacted Policy: "Position Limit Policy"
- What Changed: Signal showing BTC at 125% of limit for 5 hours
- Uncertainty: Any low-confidence signals are flagged here

**Center Column - Options:**
All options are presented symmetrically (no recommendations):
- Escalate to CFO
- Initiate Gradual Reduction
- Request Temporary Limit Increase
- Dismiss (Accept Risk)

**Right Column - Decision Capture:**
- Select an option (e.g., "Escalate to CFO")
- Enter rationale: "Given the critical severity and 5-hour duration during unusual market conditions, this requires CFO review before any position changes."
- Click "Commit Decision"

### What Happens:
1. Decision is recorded immutably
2. Exception status changes to "resolved"
3. Evidence pack is generated asynchronously
4. You're redirected to the Decision Trace view

---

## 5. View Decision Trace ("Why Did We Do This?")

### Trace View Features

**Visual Chain:**
```
Signals → Evaluation → Exception → Decision → Evidence
   (1)       (fail)     (critical)  (committed)  (sealed)
```

**Decision Summary:**
- Chosen Option: "Escalate to CFO"
- Decided By: user@example.com
- Rationale: Your entered text
- Timestamp: When committed

**Exception Context:**
- Title, severity, and key context fields

**Contributing Signals:**
- List of signals that triggered this exception
- Each shows type, source, and reliability

**Evidence Pack:**
- Hash displayed (SHA-256 prefix)
- Click "Show Raw Data" to see full JSON
- Click "Export" to download for audit

---

## 6. Export Evidence Pack (CLI)

### Using curl

```bash
# Get the decision ID from the URL (e.g., /decisions/abc-123-...)
DECISION_ID="<your-decision-id>"

# Export evidence as JSON
curl "http://localhost:8000/api/v1/evidence/${DECISION_ID}/export?format=json" \
  -o evidence-pack.json

# View the evidence
cat evidence-pack.json | python -m json.tool
```

### Evidence Pack Contents

```json
{
  "id": "...",
  "decision_id": "...",
  "content_hash": "sha256:abc123...",
  "generated_at": "2026-01-14T...",
  "evidence": {
    "decision": {
      "chosen_option_id": "escalate_to_cfo",
      "rationale": "...",
      "decided_by": "user@example.com",
      "decided_at": "..."
    },
    "exception": {
      "title": "BTC position exceeds approved limit",
      "severity": "critical",
      "context": {...}
    },
    "evaluation": {
      "result": "fail",
      "policy_version_id": "...",
      "signal_ids": [...]
    },
    "signals": [...],
    "policy": {
      "name": "Position Limit Policy",
      "version_number": 1,
      "rule_definition": {...}
    }
  }
}
```

---

## 7. Check Dashboard Stats

### API Endpoint

```bash
curl "http://localhost:8000/api/v1/stats?pack=treasury" | python -m json.tool
```

Response:
```json
{
  "pack": "treasury",
  "exceptions": {
    "open": 5,
    "by_severity": {
      "critical": 2,
      "high": 2,
      "medium": 1,
      "low": 0
    }
  },
  "decisions": {
    "total": 1,
    "last_24h": 1
  },
  "signals": {
    "total": 7,
    "last_24h": 7
  },
  "policies": {
    "total": 6,
    "active": 6
  }
}
```

### UI Dashboard

Navigate to http://localhost:3000 (home page) to see:
- Open exceptions count (colored by severity)
- Recent decisions
- Active policies
- Signal volume

---

## 8. Additional Demo Scenarios

### Work Through Multiple Exceptions

The Treasury scenarios include:

| ID | Scenario | Severity | Suggested Decision |
|----|----------|----------|-------------------|
| `btc_position_breach_critical` | BTC Position Limit | Critical | Escalate to CFO |
| `eth_volatility_spike` | ETH Volatility | High | Activate Hedges |
| `exchange_downgrade` | Exchange Downgrade | High | Reduce Exposure |
| `cash_shortfall` | Cash Forecast Variance | Critical | Initiate Cash Sweep |
| `covenant_dscr_breach` | DSCR Covenant | High | Negotiate Waiver |

### Demo Flow (Recommended Order)

1. **BTC Position Breach** - Show critical exception handling
2. **ETH Volatility** - Show market risk decisions
3. **Cash Shortfall** - Show treasury operations exception
4. **Exchange Downgrade** - Show counterparty risk management

Each decision creates an evidence pack for audit trail.

---

## 9. Replay Harness (Policy Tuning)

### Run Replay with Sample Data

```bash
# Run replay CLI (uses built-in sample signals)
python -m replay.cli run --pack treasury -v
```

Output:
```
Running replay for pack: treasury
Running with sample data...

Replay complete!
  Signals processed: 2
  Evaluations: 2
  Exceptions raised: 2
  Pass: 0, Fail: 2, Inconclusive: 0
```

### Run Replay with CSV Import

```bash
# If you have historical signal data in CSV format
python -m replay.cli ingest --file signals.csv --pack treasury -v
python -m replay.cli run --pack treasury --output replay-results.json
```

---

## 10. Cleanup

### Reset Database for Fresh Demo

```bash
# Stop services
docker compose down

# Remove volumes (deletes all data)
docker compose down -v

# Start fresh
docker compose up -d

# Re-seed
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenarios
```

---

## Key Points for Audience

1. **Deterministic Governance:** Same inputs always produce same outputs (replayable)
2. **No Recommendations:** Options are symmetric - humans make the judgment call
3. **Evidence Trail:** Every decision produces an immutable evidence pack
4. **One-Screen Decisions:** No scrolling, all context visible at once
5. **Uncertainty First-Class:** Low-confidence signals are explicitly flagged

---

## Troubleshooting

### "Connection refused" errors

```bash
# Check service status
docker compose ps

# View backend logs
docker compose logs backend

# Restart if needed
docker compose restart
```

### No exceptions showing

```bash
# Re-run seed with evaluations
docker compose exec backend python -m core.scripts.seed_fixtures --pack=treasury --scenarios --evaluate
```

### Port 3000 already in use

```bash
# Find process using port
lsof -i :3000

# Kill or stop it, then restart
docker compose restart frontend
```
