# Deployment Documentation

This directory contains deployment checklists and verification scripts for Governance OS releases.

## Sprint 3 Deployment

Sprint 3 introduces the **Full Agentic Coprocessor** - a significant feature addition that requires careful deployment verification.

### Files

| File | Purpose |
|------|---------|
| `sprint-3-checklist.md` | Complete Go/No-Go deployment checklist |
| `sprint-3-verification.sql` | Executable SQL verification queries |

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **MCP tools bypass approval gate** | CRITICAL | Verify all MCP write tools create pending proposals |
| **Traces viewer exposes PII** | CRITICAL | Verify PII scrubbing before deploy |
| **Database migration locks** | HIGH | New tables only, fast DDL |
| **Background task silent failure** | MEDIUM | Monitor task queue and logs |

### Quick Reference

**Pre-Deploy:**
```bash
# Run baseline SQL
psql -U govos -d governance_os -f docs/deployment/sprint-3-verification.sql | head -100
```

**Deploy:**
```bash
docker compose exec backend alembic upgrade head
```

**Post-Deploy:**
```bash
# Run verification SQL
psql -U govos -d governance_os -f docs/deployment/sprint-3-verification.sql
```

**Rollback:**
```bash
docker compose exec backend alembic downgrade -2  # Back to 005
```

### Checklist Summary

```
PRE-DEPLOY
[ ] Baseline counts recorded
[ ] Immutability triggers verified (3 triggers, all enabled)
[ ] All tests passing (pytest core/tests/ -v)
[ ] Staging verified
[ ] Backup created

DEPLOY
[ ] Migration 006 (pending_proposals) - < 10s
[ ] Migration 007 (agent_traces) - < 10s

POST-DEPLOY (within 5 minutes)
[ ] Data counts unchanged from baseline
[ ] Immutability triggers still active
[ ] New tables exist and empty
[ ] API health check passed
[ ] MCP approval gate verified (CRITICAL)
[ ] Traces viewer PII check (CRITICAL)
[ ] Background task running

MONITORING (24 hours)
[ ] +1h check
[ ] +4h check
[ ] +24h check
[ ] Close deployment ticket
```

### Emergency Contacts

Update these before deployment:

| Role | Name | Contact |
|------|------|---------|
| On-Call Engineer | _TBD_ | |
| Database Admin | _TBD_ | |
| Security Team | _TBD_ | |

---

## General Deployment Principles

From CLAUDE.md, these principles apply to ALL deployments:

1. **Determinism is non-negotiable** - If the system cannot be replayed with identical results, it's a regression
2. **Immutability must be preserved** - Decisions, evidence packs, and audit events are NEVER modified
3. **AI safety boundaries** - LLMs never make policy decisions or escalation judgments
4. **No recommendations in decision UI** - Options must remain symmetric

### Testing Requirements

Before any deployment:
```bash
# All kernel features must pass determinism tests
pytest core/tests/test_determinism.py -v -m critical

# Full test suite
pytest core/tests/ -v
```
