# Testing Instructions for Governance OS

This guide explains how to test the backend system.

---

## Prerequisites

You need:
- Docker + Docker Compose running
- PostgreSQL container started

---

## Quick Test (Recommended)

```bash
# 1. Start the system
make up

# Wait ~10 seconds for services to be healthy, then:

# 2. Run all tests
make test

# 3. Run only critical determinism tests
make test-critical
```

---

## What Gets Tested

### Critical Tests (MUST PASS)
These validate the core contract of the governance kernel:

1. **Determinism tests** (`test_determinism.py`)
   - ✅ Same inputs → same outputs
   - ✅ Evaluation hash consistency
   - ✅ Exception fingerprint consistency
   - ✅ Evidence pack reproducibility
   - ✅ Replay scenarios
   - ✅ Signal order independence

2. **Idempotency tests**
   - ✅ Duplicate evaluations return existing results
   - ✅ Exception deduplication via fingerprints

3. **Immutability tests**
   - ✅ Decisions cannot be updated
   - ✅ Audit events are append-only

### Service Tests
Individual service component validation:
- PolicyEngine: Policy retrieval
- Evaluator: Evaluation logic
- ExceptionEngine: Exception generation
- DecisionRecorder: Decision logging
- EvidenceGenerator: Evidence pack creation

---

## Test Database

Tests use a separate database: `governance_os_test`

The test database is created automatically on first test run.

---

## Expected Output

When tests pass, you'll see:

```
================================ test session starts ================================
core/tests/test_determinism.py::TestDeterministicFingerprinting::test_evaluation_hash_determinism PASSED
core/tests/test_determinism.py::TestDeterministicFingerprinting::test_exception_fingerprint_determinism PASSED
core/tests/test_determinism.py::TestEvaluatorDeterminism::test_evaluation_determinism_basic PASSED
core/tests/test_determinism.py::TestEvaluatorDeterminism::test_evaluation_idempotency PASSED
...

================================ X passed in X.XXs ================================
```

---

## If Tests Fail

### Database Connection Error

```
Error: could not connect to server
```

**Fix:**
```bash
# Check if postgres is running
docker compose ps

# If not running, start it
make up

# Wait 10 seconds, then retry
make test
```

### Import Errors

```
ModuleNotFoundError: No module named 'core'
```

**Fix:**
```bash
# Rebuild backend container
docker compose up --build backend
```

### Test Database Already Exists

```
database "governance_os_test" already exists
```

**Fix:**
```bash
# Drop and recreate test database
docker compose exec postgres psql -U govos -c "DROP DATABASE IF EXISTS governance_os_test;"
docker compose exec postgres psql -U govos -c "CREATE DATABASE governance_os_test;"

# Re-run tests
make test
```

---

## Test Coverage

To see test coverage report:

```bash
make test-cov
```

**Goal:** 70%+ coverage for core services

---

## Manual Verification (Without Tests)

If you want to manually verify the system works:

```bash
# 1. Start system
make up

# 2. Load fixtures
make seed

# 3. Run demo (shows full loop)
make demo-kernel

# 4. Access API
open http://localhost:8000/docs
```

This will:
- ✅ Load treasury policies
- ✅ Ingest sample signals
- ✅ Run evaluations
- ✅ Generate exceptions
- ✅ Record decisions
- ✅ Generate evidence packs

---

## Test Files

- `core/tests/conftest.py` - Pytest fixtures and configuration
- `core/tests/test_determinism.py` - **CRITICAL** determinism tests
- `core/tests/test_services.py` - Service layer tests
- `pytest.ini` - Pytest configuration

---

## Next Steps After Testing

Once tests pass:

1. ✅ Backend is verified working
2. Continue with frontend development
3. Add integration tests
4. Add performance tests
5. Prepare for production deployment

---

## Troubleshooting

### Tests are slow
- Tests create/destroy database for each test
- This is intentional for isolation
- Use `-m critical` to run only critical tests

### Need to debug a test
```bash
# Run single test with output
docker compose exec backend pytest -v -s core/tests/test_determinism.py::TestEvaluatorDeterminism::test_evaluation_determinism_basic
```

### Need to see SQL queries
```bash
# Set log level to DEBUG
docker compose exec backend pytest -v --log-cli-level=DEBUG
```

---

## Success Criteria

Tests are passing if:
- ✅ All critical tests pass (determinism, idempotency)
- ✅ No import errors
- ✅ No database connection errors
- ✅ All service tests pass

**If all tests pass, the backend kernel is production-ready!** 🎉
