# Governance OS Runbook

Operational runbook for solo ops survival. All procedures assume access to logs via `docker compose logs` or your log aggregation tool.

## Log Format

All logs are JSON-structured with the following fields:
```json
{
  "timestamp": "2025-01-14T12:00:00.000Z",
  "level": "INFO",
  "logger": "core.services.evaluator",
  "message": "Evaluation completed: fail",
  "event": "evaluation.completed",
  ...
}
```

Filter by `event` field for specific operations.

---

## Scenario: Exceptions Spike

**Symptom:** Many `exception.raised` events in short period.

### Diagnosis

```bash
# Count exceptions in last hour
docker compose logs backend --since 1h | grep '"event":"exception.raised"' | wc -l

# Check severity distribution
docker compose logs backend --since 1h | grep '"event":"exception.raised"' | \
  jq -r '.severity' | sort | uniq -c
```

### Common Causes

1. **New policy too strict** - Check recent policy changes
   ```bash
   docker compose logs backend --since 24h | grep '"event":"policy.activated"'
   ```

2. **Data quality issue** - Upstream signals may have bad data
   ```bash
   docker compose logs backend --since 1h | grep '"event":"ingestion."' | \
     jq -r '.parse_errors // 0' | awk '{sum+=$1} END {print sum}'
   ```

3. **Market event** - Legitimate spike due to external conditions (verify with business)

### Resolution

| Cause | Action |
|-------|--------|
| Policy too strict | Review policy thresholds; consider temporary adjustment |
| Bad data upstream | Contact data provider; check ingestion parse_errors |
| Market event | Normal operations - exceptions are expected |

---

## Scenario: Imports Fail

**Symptom:** `ingestion.failed` events or missing signals.

### Diagnosis

```bash
# Check for ingestion failures
docker compose logs backend --since 1h | grep '"event":"ingestion.failed"'

# Check for row-level errors
docker compose logs backend --since 1h | grep '"event":"ingestion.row_error"' | head -20

# Verify ingestion completion
docker compose logs backend --since 1h | grep '"event":"ingestion.completed"'
```

### Common Causes

1. **File format changed** - Column mapping mismatch
2. **Timestamp parsing** - New date format in source
3. **Missing required fields** - CSV missing signal_type column
4. **File not found** - Path incorrect or file missing

### Resolution

| Cause | Action |
|-------|--------|
| Column mapping | Update ColumnMapping in ingestion config |
| Timestamp format | Add new format to `_parse_timestamp()` |
| Missing fields | Contact data provider or update validation |
| File not found | Verify file path and permissions |

### Recovery

After fixing the issue:
```bash
# Re-run ingestion (idempotent - duplicates are skipped)
docker compose exec backend python -m replay.cli ingest <filepath>
```

---

## Scenario: Policy Publish Fails

**Symptom:** `policy.publish_failed` events or policy not activating.

### Diagnosis

```bash
# Check for publish failures
docker compose logs backend --since 1h | grep '"event":"policy.publish_failed"'

# Check recent policy activations
docker compose logs backend --since 24h | grep '"event":"policy.activated"'
```

### Common Causes

1. **Invalid rule_definition** - JSON schema validation failure
2. **Overlapping validity periods** - Conflict with existing version
3. **Database constraint** - Unique constraint violation
4. **Missing dependencies** - Pack not loaded

### Resolution

| Cause | Action |
|-------|--------|
| Invalid rule_definition | Validate JSON against schema before publish |
| Overlapping validity | Archive or adjust existing policy version dates |
| Database constraint | Check for duplicate policy/version combination |
| Missing pack | Ensure pack is loaded via fixtures |

---

## Scenario: Evaluation Not Producing Expected Results

**Symptom:** Policies not triggering exceptions when expected.

### Diagnosis

```bash
# Check evaluation results
docker compose logs backend --since 1h | grep '"event":"evaluation.completed"' | \
  jq -r '.result' | sort | uniq -c

# Check for cache hits (idempotency)
docker compose logs backend --since 1h | grep '"event":"evaluation.cache_hit"' | wc -l

# Check signal count in evaluations
docker compose logs backend --since 1h | grep '"event":"evaluation.completed"' | \
  jq -r '.signal_count' | sort | uniq -c
```

### Common Causes

1. **Wrong signals** - Evaluation using outdated or wrong signal set
2. **Cache hit** - Already evaluated (idempotency working correctly)
3. **Policy not active** - Policy version not in valid date range
4. **Rule logic issue** - rule_definition not matching as expected

### Resolution

Use replay with known inputs to verify behavior:
```bash
docker compose exec backend python -m replay.cli run --pack treasury --from <date> --to <date>
```

---

## Scenario: Decision Recording Fails

**Symptom:** `decision.validation_failed` events.

### Diagnosis

```bash
# Check validation failures
docker compose logs backend --since 1h | grep '"event":"decision.validation_failed"'
```

### Common Causes

1. **Exception not open** - Already resolved or invalid status
2. **Invalid option_id** - Option not in exception.options
3. **Missing rationale** - Rationale required but empty
4. **Hard override without approval** - Missing approved_by

### Resolution

Check the `error` field in the log entry for specific validation failure.

---

## Health Checks

### Quick Status Check

```bash
# API health
curl -s http://localhost:8000/health | jq

# Database connection
docker compose exec postgres pg_isready

# Container status
docker compose ps
```

### Key Metrics to Monitor

| Metric | Alert Threshold | Log Event |
|--------|-----------------|-----------|
| Exceptions/hour | > 50 | `exception.raised` |
| Parse errors/import | > 10% | `ingestion.row_error` |
| Decision validation failures | > 5/hour | `decision.validation_failed` |
| Hard overrides | Any | `decision.recorded` with `is_hard_override=true` |

---

## Log Aggregation Setup

For production, configure log shipping to your aggregation tool:

### CloudWatch (AWS)

```yaml
# docker-compose.override.yml
services:
  backend:
    logging:
      driver: awslogs
      options:
        awslogs-group: governance-os
        awslogs-region: us-east-1
```

### Datadog

```yaml
# docker-compose.override.yml
services:
  backend:
    labels:
      com.datadoghq.ad.logs: '[{"source": "governance-os", "service": "backend"}]'
```

### Basic File Logging

```bash
# Redirect to file with rotation
docker compose logs -f backend >> /var/log/govos/backend.log 2>&1 &
```

---

## Emergency Procedures

### Stop All Processing

```bash
docker compose stop backend
```

### Database Recovery

```bash
# Backup
docker compose exec postgres pg_dump -U govos governance_os > backup.sql

# Restore
docker compose exec -T postgres psql -U govos governance_os < backup.sql
```

### Roll Back Policy

1. Find last known-good policy version in audit trail
2. Archive current version (set valid_to to now)
3. Create new version with previous rule_definition
