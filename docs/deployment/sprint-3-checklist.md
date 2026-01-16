# Deployment Checklist: Sprint 3 - Full Agentic Coprocessor

**Deploy Date:** _____________
**Deploy Lead:** _____________
**Commit SHA:** _____________

---

## Summary of Changes

Sprint 3 introduces the full agentic coprocessor layer:

| Component | Change Type | Risk Level |
|-----------|-------------|------------|
| PendingProposal table | New DB table | HIGH - migration locks |
| AgentTrace table | New DB table | HIGH - PII exposure risk |
| Approvals CRUD endpoints | New API routes | MEDIUM - auth bypass risk |
| MCP write tools | New functionality | CRITICAL - approval gate bypass |
| Proposal expiration task | Background job | MEDIUM - silent failure |
| Traces viewer UI | New page | HIGH - PII exposure |

---

## Data Invariants (MUST remain true)

Before and after deployment, these invariants MUST hold:

```
[ ] All existing decisions remain immutable (trigger still active)
[ ] All existing evidence_packs remain immutable (trigger still active)
[ ] All existing audit_events remain immutable (trigger still active)
[ ] Hard override constraint (ck_hard_override_requires_approval) still enforced
[ ] No orphaned foreign key relationships
[ ] All existing users retain their roles
[ ] Evaluation determinism: same inputs produce same outputs
```

---

## PHASE 1: Pre-Deploy Verification

### 1.1 Environment Verification

```bash
# Verify database connectivity
[ ] docker compose exec postgres pg_isready -U govos

# Verify current migration state
[ ] docker compose exec backend alembic current
# Expected: 005_add_immutability_triggers (head)

# Check for pending migrations
[ ] docker compose exec backend alembic history --verbose
```

### 1.2 Baseline Data Counts (SAVE THESE VALUES)

Run these queries and record results before deployment:

```sql
-- ===========================================
-- BASELINE COUNTS - RECORD BEFORE DEPLOY
-- ===========================================

-- Table row counts
SELECT 'policies' as table_name, COUNT(*) as count FROM policies
UNION ALL SELECT 'policy_versions', COUNT(*) FROM policy_versions
UNION ALL SELECT 'signals', COUNT(*) FROM signals
UNION ALL SELECT 'evaluations', COUNT(*) FROM evaluations
UNION ALL SELECT 'exceptions', COUNT(*) FROM exceptions
UNION ALL SELECT 'decisions', COUNT(*) FROM decisions
UNION ALL SELECT 'evidence_packs', COUNT(*) FROM evidence_packs
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events
UNION ALL SELECT 'users', COUNT(*) FROM users;

-- Decision type distribution (for comparison after new tables)
SELECT decision_type, is_hard_override, COUNT(*)
FROM decisions
GROUP BY decision_type, is_hard_override;

-- Exception status distribution
SELECT status, COUNT(*)
FROM exceptions
GROUP BY status;

-- User role distribution
SELECT role, is_active, COUNT(*)
FROM users
GROUP BY role, is_active;

-- Record latest audit event ID
SELECT MAX(id) as latest_audit_event_id,
       MAX(occurred_at) as latest_audit_time
FROM audit_events;
```

**Baseline Values:**

| Metric | Pre-Deploy Value | Post-Deploy Value | Status |
|--------|------------------|-------------------|--------|
| policies count | | | |
| policy_versions count | | | |
| signals count | | | |
| evaluations count | | | |
| exceptions count | | | |
| decisions count | | | |
| evidence_packs count | | | |
| audit_events count | | | |
| users count | | | |
| latest_audit_event_id | | | |

### 1.3 Verify Immutability Triggers Active

```sql
-- Must return 3 rows (decisions, evidence_packs, audit_events)
SELECT tgname, tgrelid::regclass as table_name, tgenabled
FROM pg_trigger
WHERE tgname LIKE '%_immutable';

-- Expected output:
-- tgname                    | table_name     | tgenabled
-- decisions_immutable       | decisions      | O
-- evidence_packs_immutable  | evidence_packs | O
-- audit_events_immutable    | audit_events   | O
```

**Result:** [ ] 3 triggers confirmed active

### 1.4 Pre-Deploy Test Suite

```bash
# Run full test suite
[ ] pytest core/tests/ -v --tb=short

# Run critical determinism tests specifically
[ ] pytest core/tests/test_determinism.py -v -m critical

# All tests must pass before proceeding
```

**Test Results:**
- Total tests: ____
- Passed: ____
- Failed: ____ (STOP if > 0)

### 1.5 Staging Verification

```bash
# Deploy to staging first
[ ] Deploy Sprint 3 to staging environment
[ ] Run staging smoke tests
[ ] Verify new tables exist on staging
[ ] Test MCP tools on staging with approval gate
[ ] Verify traces viewer does not expose PII on staging
```

### 1.6 Backup Confirmation

```bash
# Create pre-deploy backup
[ ] pg_dump -Fc governance_os > backup_pre_sprint3_$(date +%Y%m%d_%H%M%S).dump

# Verify backup integrity
[ ] pg_restore --list backup_pre_sprint3_*.dump | head -20

# Store backup location: _________________________________
```

---

## PHASE 2: Migration Risk Assessment

### 2.1 Migration 006: Add PendingProposal Table

**Expected Migration:**

```sql
-- New enum type
CREATE TYPE proposal_status AS ENUM ('pending', 'approved', 'rejected', 'expired');
CREATE TYPE proposal_type AS ENUM ('signal', 'policy_draft', 'exception_dismiss');

-- New table
CREATE TABLE pending_proposals (
    id UUID PRIMARY KEY,
    proposal_type proposal_type NOT NULL,
    proposed_by VARCHAR(255) NOT NULL,
    proposed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload JSONB NOT NULL,
    status proposal_status NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    -- Foreign keys depend on proposal_type
    exception_id UUID REFERENCES exceptions(id),
    policy_id UUID REFERENCES policies(id)
);

CREATE INDEX idx_pending_proposals_status ON pending_proposals(status);
CREATE INDEX idx_pending_proposals_expires ON pending_proposals(expires_at);
```

**Risk Assessment:**

| Risk | Mitigation |
|------|------------|
| Table creation locks pg_class | Minimal - empty table, fast DDL |
| Enum creation is fast | Low risk |
| Index creation on empty table | Instant |

**Estimated Runtime:** < 5 seconds

### 2.2 Migration 007: Add AgentTrace Table

**Expected Migration:**

```sql
-- New table for agent traces
CREATE TABLE agent_traces (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(100) NOT NULL,
    trace_id VARCHAR(255) NOT NULL UNIQUE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    -- Input/output (may contain PII - needs review)
    input_summary JSONB NOT NULL,
    output_summary JSONB,
    -- Execution metadata
    tool_calls JSONB NOT NULL DEFAULT '[]',
    error_message TEXT,
    -- Provenance
    triggered_by VARCHAR(255),
    related_exception_id UUID REFERENCES exceptions(id),
    related_decision_id UUID REFERENCES decisions(id)
);

CREATE INDEX idx_agent_traces_trace_id ON agent_traces(trace_id);
CREATE INDEX idx_agent_traces_agent_type ON agent_traces(agent_type, started_at);
CREATE INDEX idx_agent_traces_status ON agent_traces(status);
```

**Risk Assessment:**

| Risk | Mitigation |
|------|------------|
| PII in input_summary/output_summary | Verify PII scrubbing before deploy |
| Large JSONB columns | Monitor storage growth |
| No immutability trigger (intentional) | Traces are operational, not audit |

**Estimated Runtime:** < 5 seconds

### 2.3 Pre-Migration Validation

```sql
-- Verify no conflicting type names
SELECT typname FROM pg_type
WHERE typname IN ('proposal_status', 'proposal_type');
-- Expected: 0 rows

-- Verify no conflicting table names
SELECT tablename FROM pg_tables
WHERE tablename IN ('pending_proposals', 'agent_traces');
-- Expected: 0 rows

-- Check current schema version
SELECT version_num FROM alembic_version;
-- Expected: 005_add_immutability_triggers
```

---

## PHASE 3: Deploy Execution

### 3.1 Deploy Steps (In Order)

```
| Step | Command | Est. Time | Rollback | Completed |
|------|---------|-----------|----------|-----------|
| 1 | Enable maintenance mode | Instant | Disable | [ ] |
| 2 | Stop background workers | < 30s | Start workers | [ ] |
| 3 | Deploy new code (git pull/docker pull) | 1-2 min | git checkout HEAD~1 | [ ] |
| 4 | Run migration 006 | < 10s | alembic downgrade -1 | [ ] |
| 5 | Run migration 007 | < 10s | alembic downgrade -1 | [ ] |
| 6 | Verify migrations | < 1 min | See below | [ ] |
| 7 | Start background workers | < 30s | N/A | [ ] |
| 8 | Restart API containers | < 1 min | N/A | [ ] |
| 9 | Disable maintenance mode | Instant | N/A | [ ] |
```

### 3.2 Migration Execution Commands

```bash
# Step 4: Migration 006
[ ] docker compose exec backend alembic upgrade +1
# Verify: "Running upgrade 005_add_immutability_triggers -> 006_add_pending_proposals"

# Step 5: Migration 007
[ ] docker compose exec backend alembic upgrade +1
# Verify: "Running upgrade 006_add_pending_proposals -> 007_add_agent_traces"

# Step 6: Verify current head
[ ] docker compose exec backend alembic current
# Expected: 007_add_agent_traces (head)
```

### 3.3 Immediate Post-Migration Verification

```sql
-- Verify new tables exist
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('pending_proposals', 'agent_traces');
-- Expected: 2 rows

-- Verify new enum types exist
SELECT typname FROM pg_type
WHERE typname IN ('proposal_status', 'proposal_type');
-- Expected: 2 rows

-- Verify indexes created
SELECT indexname FROM pg_indexes
WHERE tablename IN ('pending_proposals', 'agent_traces');
-- Expected: 5+ indexes

-- CRITICAL: Verify immutability triggers still active
SELECT tgname, tgrelid::regclass
FROM pg_trigger
WHERE tgname LIKE '%_immutable';
-- Expected: 3 rows (unchanged)
```

---

## PHASE 4: Post-Deploy Verification (Within 5 Minutes)

### 4.1 Data Integrity Verification

```sql
-- Compare with baseline counts (must be unchanged)
SELECT 'decisions' as table_name, COUNT(*) as count FROM decisions
UNION ALL SELECT 'evidence_packs', COUNT(*) FROM evidence_packs
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events;

-- Verify no data corruption in existing tables
SELECT COUNT(*) as orphaned_decisions
FROM decisions d
LEFT JOIN exceptions e ON d.exception_id = e.id
WHERE e.id IS NULL;
-- Expected: 0

SELECT COUNT(*) as orphaned_evidence_packs
FROM evidence_packs ep
LEFT JOIN decisions d ON ep.decision_id = d.id
WHERE d.id IS NULL;
-- Expected: 0

-- Verify hard override constraint still enforced
SELECT COUNT(*) as invalid_hard_overrides
FROM decisions
WHERE is_hard_override = true
AND (approved_by IS NULL OR approved_at IS NULL);
-- Expected: 0
```

### 4.2 New Table Verification

```sql
-- New tables should be empty initially
SELECT COUNT(*) FROM pending_proposals;
-- Expected: 0

SELECT COUNT(*) FROM agent_traces;
-- Expected: 0

-- Verify foreign key constraints work
-- (These should fail with FK violation if constraints are correct)
-- DO NOT RUN IN PRODUCTION - just verify constraints exist:
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE conrelid IN ('pending_proposals'::regclass, 'agent_traces'::regclass)
AND contype = 'f';
```

### 4.3 API Health Check

```bash
# Health endpoint
[ ] curl -s http://localhost:8000/health | jq .
# Expected: {"status": "healthy", "database": "connected"}

# API docs accessible
[ ] curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
# Expected: 200

# Existing endpoints still work
[ ] curl -s http://localhost:8000/api/v1/stats | jq .
# Expected: Valid JSON with counts
```

### 4.4 New Endpoints Verification

```bash
# Approvals endpoints (expect empty list or 401 if auth required)
[ ] curl -s http://localhost:8000/api/v1/approvals | jq .
# Expected: [] or {"detail": "Not authenticated"}

# Traces endpoint (expect empty list)
[ ] curl -s http://localhost:8000/api/v1/traces | jq .
# Expected: []
```

### 4.5 MCP Tool Verification (CRITICAL)

```bash
# Test propose_signal tool - MUST require approval
[ ] Test propose_signal with valid signal data
# Expected: Returns pending proposal, NOT direct signal creation

# Test propose_policy_draft tool - MUST require approval
[ ] Test propose_policy_draft with valid policy data
# Expected: Returns pending proposal, NOT direct policy creation

# Test dismiss_exception tool - MUST require approval
[ ] Test dismiss_exception with valid exception ID
# Expected: Returns pending proposal, NOT direct dismissal

# CRITICAL: Verify direct writes are blocked
# Attempt direct signal creation via MCP (should fail or require proposal)
```

**MCP Approval Gate Test Results:**

| Tool | Creates Proposal | Requires Approval | Direct Write Blocked |
|------|------------------|-------------------|---------------------|
| propose_signal | [ ] | [ ] | [ ] |
| propose_policy_draft | [ ] | [ ] | [ ] |
| dismiss_exception | [ ] | [ ] | [ ] |

### 4.6 Traces Viewer PII Check (CRITICAL)

```bash
# Navigate to traces viewer
[ ] Open http://localhost:3000/traces

# Verify NO PII visible in:
[ ] Input summary display - should show sanitized version
[ ] Output summary display - should show sanitized version
[ ] Tool call arguments - should redact sensitive fields

# Specific PII fields to check are NOT displayed:
[ ] User email addresses
[ ] User full names (display_name)
[ ] Account numbers
[ ] Authentication tokens
[ ] Any payload marked as sensitive
```

---

## PHASE 5: Background Task Verification

### 5.1 Proposal Expiration Task

```bash
# Verify task is registered
[ ] docker compose exec backend python -c "from core.tasks import proposal_expiration; print('Task registered')"

# Check task schedule
[ ] docker compose exec backend celery -A core.celery inspect scheduled
# Expected: proposal_expiration task scheduled

# Verify task can run manually (dry-run)
[ ] docker compose exec backend python -c "
from core.tasks import expire_pending_proposals
result = expire_pending_proposals(dry_run=True)
print(f'Would expire {result} proposals')
"
```

### 5.2 Task Error Monitoring

```bash
# Check for task errors in logs
[ ] docker compose logs --tail=100 backend | grep -i "task\|error\|exception"

# Verify dead letter queue is empty (if using message broker)
[ ] docker compose exec redis redis-cli LLEN celery_dead_letter
# Expected: 0
```

### 5.3 Create Test Proposal for Expiration

```sql
-- Insert test proposal with past expiration (for manual verification)
INSERT INTO pending_proposals (
    id, proposal_type, proposed_by, proposed_at,
    payload, status, expires_at
) VALUES (
    gen_random_uuid(),
    'signal',
    'deploy_test',
    NOW(),
    '{"test": true}'::jsonb,
    'pending',
    NOW() - INTERVAL '1 hour'  -- Already expired
);

-- Run expiration task
-- Expected: Test proposal should be marked 'expired'

-- Verify
SELECT id, status, expires_at FROM pending_proposals WHERE proposed_by = 'deploy_test';
-- Expected: status = 'expired'

-- Cleanup test data
DELETE FROM pending_proposals WHERE proposed_by = 'deploy_test';
```

---

## PHASE 6: Rollback Procedures

### 6.1 Rollback Decision Tree

```
Is the system functional?
    |
    +-- YES --> Monitor for 24 hours, proceed to Phase 7
    |
    +-- NO --> What is broken?
                |
                +-- Database migration failed
                |   --> Execute Rollback Plan A
                |
                +-- New API endpoints broken
                |   --> Execute Rollback Plan B
                |
                +-- MCP tools bypassing approval
                |   --> CRITICAL: Execute Rollback Plan C immediately
                |
                +-- Background task failing
                |   --> Execute Rollback Plan D
                |
                +-- Traces viewer exposing PII
                    --> CRITICAL: Execute Rollback Plan E immediately
```

### 6.2 Rollback Plan A: Database Migration

```bash
# Revert migration 007
[ ] docker compose exec backend alembic downgrade -1
# Verify: "Running downgrade 007_add_agent_traces -> 006_add_pending_proposals"

# Revert migration 006
[ ] docker compose exec backend alembic downgrade -1
# Verify: "Running downgrade 006_add_pending_proposals -> 005_add_immutability_triggers"

# Verify rollback complete
[ ] docker compose exec backend alembic current
# Expected: 005_add_immutability_triggers (head)

# Restart services
[ ] docker compose restart backend
```

### 6.3 Rollback Plan B: API Endpoints Only

```bash
# If only new endpoints are broken, deploy previous code without migration rollback
[ ] git checkout HEAD~1 -- core/api/approvals.py core/api/traces.py
[ ] docker compose build backend
[ ] docker compose restart backend

# Note: New tables remain but are unused
```

### 6.4 Rollback Plan C: MCP Approval Gate Bypass (CRITICAL)

```bash
# IMMEDIATE ACTIONS:
# 1. Disable MCP server entirely
[ ] docker compose stop mcp-server

# 2. Revoke any pending proposals created without approval
[ ] docker compose exec postgres psql -U govos -c "
    UPDATE pending_proposals
    SET status = 'rejected',
        review_notes = 'Emergency rollback - approval gate failure'
    WHERE status = 'pending';
"

# 3. Deploy previous MCP code
[ ] git checkout HEAD~1 -- mcp/
[ ] docker compose build mcp-server
[ ] docker compose start mcp-server

# 4. Verify approval gate is enforced
# Run MCP tool tests again (see Phase 4.5)
```

### 6.5 Rollback Plan D: Background Task

```bash
# Disable the problematic task
[ ] docker compose exec backend celery -A core.celery control revoke proposal_expiration

# Or stop all workers temporarily
[ ] docker compose stop celery-worker

# Fix task code and redeploy
[ ] git checkout HEAD~1 -- core/tasks/proposal_expiration.py
[ ] docker compose build backend
[ ] docker compose start celery-worker
```

### 6.6 Rollback Plan E: PII Exposure (CRITICAL)

```bash
# IMMEDIATE ACTIONS:
# 1. Disable traces viewer route
[ ] Add "TRACES_VIEWER_ENABLED=false" to environment
[ ] docker compose restart frontend

# 2. Clear any cached trace data
[ ] docker compose exec redis redis-cli FLUSHALL

# 3. Purge any traces that may contain PII
[ ] docker compose exec postgres psql -U govos -c "
    -- Only if traces exist and contain PII
    TRUNCATE agent_traces;
"

# 4. Deploy fixed frontend with PII scrubbing
[ ] git checkout HEAD~1 -- ui/app/traces/
[ ] docker compose build frontend
[ ] docker compose restart frontend
```

### 6.7 Full Rollback (Nuclear Option)

```bash
# Only if all else fails
# WARNING: This loses Sprint 3 data

# 1. Stop all services
[ ] docker compose down

# 2. Restore database from backup
[ ] pg_restore -c -d governance_os backup_pre_sprint3_*.dump

# 3. Deploy previous release
[ ] git checkout v2.0.0  # or previous tag
[ ] docker compose up -d --build

# 4. Verify system is functional
[ ] curl -s http://localhost:8000/health
[ ] Run smoke tests
```

---

## PHASE 7: Monitoring Plan (First 24 Hours)

### 7.1 Metrics to Monitor

| Metric | Alert Threshold | Dashboard | Check At |
|--------|-----------------|-----------|----------|
| API error rate | > 1% for 5 min | /dashboard/api | +1h, +4h, +24h |
| API latency p99 | > 500ms for 5 min | /dashboard/api | +1h, +4h, +24h |
| Background task failures | Any failure | /dashboard/tasks | +1h, +4h, +24h |
| Pending proposals > 24h | Any count > 0 | /dashboard/proposals | +4h, +24h |
| Database connections | > 80% pool | /dashboard/db | +1h, +4h, +24h |
| Agent trace errors | > 5% error rate | /dashboard/traces | +1h, +4h, +24h |

### 7.2 Log Queries

```bash
# Check for errors in last hour
[ ] docker compose logs --since 1h backend 2>&1 | grep -i "error\|exception\|failed"

# Check MCP server logs
[ ] docker compose logs --since 1h mcp-server 2>&1 | grep -i "error\|exception\|failed"

# Check background task logs
[ ] docker compose logs --since 1h celery-worker 2>&1 | grep -i "error\|exception\|failed"
```

### 7.3 Console Verification Commands

```python
# Run these in Django/FastAPI shell or Python REPL

# Check proposal creation is working
from core.models import PendingProposal
print(f"Pending proposals: {PendingProposal.query.filter_by(status='pending').count()}")

# Check traces are being recorded
from core.models import AgentTrace
print(f"Agent traces: {AgentTrace.query.count()}")
print(f"Failed traces: {AgentTrace.query.filter_by(status='error').count()}")

# Spot check recent traces for PII (should be empty/scrubbed)
recent_traces = AgentTrace.query.order_by(AgentTrace.started_at.desc()).limit(5).all()
for t in recent_traces:
    print(f"Trace {t.trace_id}: input_summary keys = {t.input_summary.keys()}")
    # Verify no PII fields present
```

### 7.4 Scheduled Checks

| Time | Action | Completed |
|------|--------|-----------|
| +1 hour | Run post-deploy queries (4.1) | [ ] |
| +1 hour | Check error logs (7.2) | [ ] |
| +1 hour | Verify background task ran | [ ] |
| +4 hours | Full health check | [ ] |
| +4 hours | Review any pending proposals | [ ] |
| +24 hours | Full audit of new tables | [ ] |
| +24 hours | Review agent trace patterns | [ ] |
| +24 hours | Close deployment ticket | [ ] |

---

## PHASE 8: Sign-Off

### 8.1 Go/No-Go Checklist Summary

**Pre-Deploy:**
- [ ] Baseline counts recorded
- [ ] Immutability triggers verified
- [ ] All tests passing
- [ ] Staging verified
- [ ] Backup created

**Deploy:**
- [ ] Migration 006 successful
- [ ] Migration 007 successful
- [ ] API containers restarted

**Post-Deploy:**
- [ ] Data counts unchanged
- [ ] Immutability triggers still active
- [ ] API health check passed
- [ ] MCP approval gate verified
- [ ] Traces viewer PII check passed
- [ ] Background task running

**Monitoring:**
- [ ] Alerts configured
- [ ] +1h check completed
- [ ] +4h check completed
- [ ] +24h check completed

### 8.2 Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Deploy Lead | | | |
| Backend Engineer | | | |
| Security Review | | | |
| Product Owner | | | |

### 8.3 Post-Deploy Notes

```
Issues encountered:




Resolution steps:




Follow-up items:




```

---

## Appendix A: Quick Reference Commands

```bash
# Migration commands
alembic current                    # Show current version
alembic upgrade head               # Upgrade to latest
alembic downgrade -1               # Rollback one version
alembic history --verbose          # Show migration history

# Docker commands
docker compose up -d               # Start all services
docker compose logs -f backend     # Follow backend logs
docker compose exec backend bash   # Shell into backend
docker compose restart backend     # Restart backend only

# Database commands
psql -U govos -d governance_os     # Connect to database
\dt                                # List tables
\d+ table_name                     # Describe table
SELECT * FROM alembic_version;     # Check migration version

# Test commands
pytest core/tests/ -v              # Run all tests
pytest -x                          # Stop on first failure
pytest --tb=short                  # Short traceback
```

## Appendix B: Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| On-Call Engineer | | |
| Database Admin | | |
| Security Team | | |
| Product Owner | | |

---

**Document Version:** 1.0
**Last Updated:** 2026-01-14
**Next Review:** Before Sprint 3 deploy
