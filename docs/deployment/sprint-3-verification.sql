-- ============================================================================
-- Sprint 3 Deployment Verification SQL
-- ============================================================================
-- This script contains all SQL queries needed for Sprint 3 deployment
-- Run sections as indicated in the deployment checklist
-- ============================================================================

-- ============================================================================
-- SECTION 1: PRE-DEPLOY BASELINE COUNTS
-- Run BEFORE deployment and save results
-- ============================================================================

-- 1.1 Table row counts (baseline)
\echo '=== 1.1 Table Row Counts ==='
SELECT 'policies' as table_name, COUNT(*) as count FROM policies
UNION ALL SELECT 'policy_versions', COUNT(*) FROM policy_versions
UNION ALL SELECT 'signals', COUNT(*) FROM signals
UNION ALL SELECT 'evaluations', COUNT(*) FROM evaluations
UNION ALL SELECT 'exceptions', COUNT(*) FROM exceptions
UNION ALL SELECT 'decisions', COUNT(*) FROM decisions
UNION ALL SELECT 'evidence_packs', COUNT(*) FROM evidence_packs
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY table_name;

-- 1.2 Decision type distribution
\echo '=== 1.2 Decision Type Distribution ==='
SELECT
    decision_type,
    is_hard_override,
    COUNT(*) as count
FROM decisions
GROUP BY decision_type, is_hard_override
ORDER BY decision_type, is_hard_override;

-- 1.3 Exception status distribution
\echo '=== 1.3 Exception Status Distribution ==='
SELECT
    status,
    COUNT(*) as count
FROM exceptions
GROUP BY status
ORDER BY status;

-- 1.4 User role distribution
\echo '=== 1.4 User Role Distribution ==='
SELECT
    role,
    is_active,
    COUNT(*) as count
FROM users
GROUP BY role, is_active
ORDER BY role, is_active;

-- 1.5 Latest audit event marker
\echo '=== 1.5 Latest Audit Event ==='
SELECT
    MAX(id) as latest_audit_event_id,
    MAX(occurred_at) as latest_audit_time
FROM audit_events;

-- 1.6 Current schema version
\echo '=== 1.6 Current Schema Version ==='
SELECT version_num FROM alembic_version;

-- ============================================================================
-- SECTION 2: PRE-MIGRATION VALIDATION
-- Verify no conflicts before running migrations
-- ============================================================================

-- 2.1 Check for conflicting enum types
\echo '=== 2.1 Check Conflicting Enum Types ==='
SELECT typname, typnamespace::regnamespace as schema
FROM pg_type
WHERE typname IN ('proposal_status', 'proposal_type')
AND typnamespace = 'public'::regnamespace;
-- Expected: 0 rows (no conflicts)

-- 2.2 Check for conflicting table names
\echo '=== 2.2 Check Conflicting Table Names ==='
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('pending_proposals', 'agent_traces');
-- Expected: 0 rows (no conflicts)

-- 2.3 Verify immutability triggers exist
\echo '=== 2.3 Verify Immutability Triggers ==='
SELECT
    tgname as trigger_name,
    tgrelid::regclass as table_name,
    CASE tgenabled
        WHEN 'O' THEN 'ENABLED'
        WHEN 'D' THEN 'DISABLED'
        WHEN 'R' THEN 'REPLICA'
        WHEN 'A' THEN 'ALWAYS'
    END as status
FROM pg_trigger
WHERE tgname LIKE '%_immutable'
ORDER BY table_name;
-- Expected: 3 rows (decisions, evidence_packs, audit_events), all ENABLED

-- ============================================================================
-- SECTION 3: POST-MIGRATION VERIFICATION
-- Run immediately after migrations complete
-- ============================================================================

-- 3.1 Verify new tables created
\echo '=== 3.1 Verify New Tables Created ==='
SELECT
    tablename,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('pending_proposals', 'agent_traces');
-- Expected: 2 rows

-- 3.2 Verify new enum types created
\echo '=== 3.2 Verify New Enum Types ==='
SELECT typname, typnamespace::regnamespace as schema
FROM pg_type
WHERE typname IN ('proposal_status', 'proposal_type');
-- Expected: 2 rows

-- 3.3 Verify indexes on new tables
\echo '=== 3.3 Verify New Indexes ==='
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('pending_proposals', 'agent_traces')
ORDER BY tablename, indexname;
-- Expected: Multiple indexes

-- 3.4 Verify foreign key constraints
\echo '=== 3.4 Verify Foreign Key Constraints ==='
SELECT
    conname as constraint_name,
    conrelid::regclass as table_name,
    confrelid::regclass as references_table
FROM pg_constraint
WHERE conrelid IN (
    'pending_proposals'::regclass,
    'agent_traces'::regclass
)
AND contype = 'f'
ORDER BY table_name, constraint_name;

-- 3.5 Verify new tables are empty
\echo '=== 3.5 Verify New Tables Empty ==='
SELECT 'pending_proposals' as table_name, COUNT(*) as count FROM pending_proposals
UNION ALL
SELECT 'agent_traces', COUNT(*) FROM agent_traces;
-- Expected: Both 0

-- 3.6 Verify schema version updated
\echo '=== 3.6 Verify Schema Version ==='
SELECT version_num FROM alembic_version;
-- Expected: 007_add_agent_traces

-- ============================================================================
-- SECTION 4: DATA INTEGRITY VERIFICATION
-- Verify existing data is unchanged and constraints hold
-- ============================================================================

-- 4.1 Compare counts with baseline (manually compare with pre-deploy values)
\echo '=== 4.1 Post-Deploy Counts (Compare with Baseline) ==='
SELECT 'policies' as table_name, COUNT(*) as count FROM policies
UNION ALL SELECT 'policy_versions', COUNT(*) FROM policy_versions
UNION ALL SELECT 'signals', COUNT(*) FROM signals
UNION ALL SELECT 'evaluations', COUNT(*) FROM evaluations
UNION ALL SELECT 'exceptions', COUNT(*) FROM exceptions
UNION ALL SELECT 'decisions', COUNT(*) FROM decisions
UNION ALL SELECT 'evidence_packs', COUNT(*) FROM evidence_packs
UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY table_name;

-- 4.2 Check for orphaned decisions
\echo '=== 4.2 Check Orphaned Decisions ==='
SELECT COUNT(*) as orphaned_decisions
FROM decisions d
LEFT JOIN exceptions e ON d.exception_id = e.id
WHERE e.id IS NULL;
-- Expected: 0

-- 4.3 Check for orphaned evidence packs
\echo '=== 4.3 Check Orphaned Evidence Packs ==='
SELECT COUNT(*) as orphaned_evidence_packs
FROM evidence_packs ep
LEFT JOIN decisions d ON ep.decision_id = d.id
WHERE d.id IS NULL;
-- Expected: 0

-- 4.4 Verify hard override constraint still enforced
\echo '=== 4.4 Verify Hard Override Constraint ==='
SELECT COUNT(*) as invalid_hard_overrides
FROM decisions
WHERE is_hard_override = true
AND (approved_by IS NULL OR approved_at IS NULL);
-- Expected: 0

-- 4.5 Verify immutability triggers still active (repeat from 2.3)
\echo '=== 4.5 Verify Immutability Triggers Still Active ==='
SELECT
    tgname as trigger_name,
    tgrelid::regclass as table_name,
    CASE tgenabled
        WHEN 'O' THEN 'ENABLED'
        WHEN 'D' THEN 'DISABLED'
        WHEN 'R' THEN 'REPLICA'
        WHEN 'A' THEN 'ALWAYS'
    END as status
FROM pg_trigger
WHERE tgname LIKE '%_immutable'
ORDER BY table_name;
-- Expected: 3 rows, all ENABLED

-- ============================================================================
-- SECTION 5: FUNCTIONAL VERIFICATION
-- Test that new functionality works correctly
-- ============================================================================

-- 5.1 Test pending_proposals insert (cleanup after)
\echo '=== 5.1 Test Pending Proposals Insert ==='
BEGIN;
INSERT INTO pending_proposals (
    id, proposal_type, proposed_by, proposed_at,
    payload, status, expires_at
) VALUES (
    gen_random_uuid(),
    'signal',
    'verification_test',
    NOW(),
    '{"test": true, "purpose": "deployment_verification"}'::jsonb,
    'pending',
    NOW() + INTERVAL '1 hour'
);
SELECT 'INSERT successful' as result;
ROLLBACK;
-- Expected: INSERT successful, then rollback

-- 5.2 Test agent_traces insert (cleanup after)
\echo '=== 5.2 Test Agent Traces Insert ==='
BEGIN;
INSERT INTO agent_traces (
    id, agent_type, trace_id, started_at, status,
    input_summary, tool_calls, triggered_by
) VALUES (
    gen_random_uuid(),
    'narrative_agent',
    'test_trace_' || gen_random_uuid(),
    NOW(),
    'completed',
    '{"test": true}'::jsonb,
    '[]'::jsonb,
    'verification_test'
);
SELECT 'INSERT successful' as result;
ROLLBACK;
-- Expected: INSERT successful, then rollback

-- 5.3 Test immutability still enforced on decisions
\echo '=== 5.3 Test Decision Immutability ==='
DO $$
BEGIN
    -- This should fail with an exception
    UPDATE decisions SET rationale = 'HACKED' WHERE id = (SELECT id FROM decisions LIMIT 1);
    RAISE NOTICE 'ERROR: Immutability trigger not working!';
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'SUCCESS: Immutability trigger blocked UPDATE as expected';
END $$;

-- ============================================================================
-- SECTION 6: MONITORING QUERIES
-- Use these during the 24-hour monitoring period
-- ============================================================================

-- 6.1 Pending proposals status
\echo '=== 6.1 Pending Proposals Status ==='
SELECT
    status,
    proposal_type,
    COUNT(*) as count,
    MIN(proposed_at) as oldest,
    MAX(proposed_at) as newest
FROM pending_proposals
GROUP BY status, proposal_type
ORDER BY status, proposal_type;

-- 6.2 Expired proposals that need attention
\echo '=== 6.2 Expired Proposals Needing Attention ==='
SELECT
    id,
    proposal_type,
    proposed_by,
    proposed_at,
    expires_at,
    status
FROM pending_proposals
WHERE status = 'pending'
AND expires_at < NOW()
ORDER BY expires_at;
-- Expected: 0 (expiration task should handle these)

-- 6.3 Agent trace summary
\echo '=== 6.3 Agent Trace Summary ==='
SELECT
    agent_type,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM agent_traces
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY agent_type, status
ORDER BY agent_type, status;

-- 6.4 Agent trace errors
\echo '=== 6.4 Agent Trace Errors ==='
SELECT
    id,
    agent_type,
    trace_id,
    started_at,
    error_message
FROM agent_traces
WHERE status = 'error'
AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC
LIMIT 10;

-- 6.5 Recent audit events (verify system still logging)
\echo '=== 6.5 Recent Audit Events ==='
SELECT
    event_type,
    COUNT(*) as count,
    MAX(occurred_at) as most_recent
FROM audit_events
WHERE occurred_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type
ORDER BY count DESC;

-- ============================================================================
-- SECTION 7: ROLLBACK VERIFICATION
-- Use after rollback to verify system is restored
-- ============================================================================

-- 7.1 Verify new tables dropped (after rollback)
\echo '=== 7.1 Verify New Tables Dropped ==='
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('pending_proposals', 'agent_traces');
-- Expected after rollback: 0 rows

-- 7.2 Verify new enum types dropped (after rollback)
\echo '=== 7.2 Verify New Enum Types Dropped ==='
SELECT typname
FROM pg_type
WHERE typname IN ('proposal_status', 'proposal_type');
-- Expected after rollback: 0 rows

-- 7.3 Verify schema version reverted (after rollback)
\echo '=== 7.3 Verify Schema Version Reverted ==='
SELECT version_num FROM alembic_version;
-- Expected after rollback: 005_add_immutability_triggers

-- ============================================================================
-- END OF VERIFICATION SCRIPT
-- ============================================================================
