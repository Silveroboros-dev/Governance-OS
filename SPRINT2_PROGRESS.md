# Sprint 2 Progress Report

**Status:** COMPLETE
**Duration:** January 2025
**Theme:** Packs + Replay + AI Thin-Slice

---

## Summary

Sprint 2 delivered two parallel tracks building on Sprint 1's deterministic kernel:

- **Track A (Packs + Replay):** Wealth pack, CSV ingestion, replay harness, exception metrics
- **Track B (AI Thin-Slice):** MCP server (read-only), NarrativeAgent, Evals (anti-hallucination)

---

## Deliverables

### Track A: Packs + Replay

#### Wealth Pack (`/packs/wealth/`)
| Component | Count | Description |
|-----------|-------|-------------|
| Signal Types | 8 | portfolio_drift, rebalancing_required, suitability_mismatch, concentration_breach, tax_loss_harvest_opportunity, client_cash_withdrawal, market_correlation_spike, fee_schedule_change |
| Policies | 8 | One policy per signal type with threshold_breach rules |
| Option Templates | 8 | Symmetric decision options (no recommendations) |
| Demo Scenarios | 7 | Realistic wealth management scenarios |

#### Replay Harness (`/replay/`)
| Module | Purpose |
|--------|---------|
| `csv_ingestor.py` | CSV import with SHA256 provenance tracking |
| `harness.py` | Deterministic policy evaluation in isolated namespaces |
| `comparison.py` | Compare replay vs production (before/after policy changes) |
| `metrics.py` | Exception budgets, policy metrics, replay analytics |
| `cli.py` | Command-line interface for replay operations |

**Key Features:**
- Full provenance tracking (source file, row number, import batch ID, file hash)
- Deterministic evaluation (input_hash for reproducibility)
- Exception fingerprinting for deduplication
- Budget tracking (daily/weekly limits with warning thresholds)

### Track B: AI Thin-Slice

#### MCP Server (`/mcp_server/`)
Read-only tools exposing kernel state for AI agents:

| Tool | Description |
|------|-------------|
| `get_open_exceptions` | List open exceptions with filters |
| `get_exception_detail` | Full exception context |
| `get_policies` | Active policies with versions |
| `get_evidence_pack` | Evidence bundle for a decision |
| `search_decisions` | Search decision history |
| `get_recent_signals` | Recent signals by type |

**Safety:** v0 is strictly read-only. No write tools exposed.

#### NarrativeAgent (`/coprocessor/`)
| Component | Purpose |
|-----------|---------|
| `agents/narrative_agent.py` | Drafts memos grounded to evidence IDs |
| `schemas/narrative.py` | NarrativeMemo, NarrativeClaim, EvidenceReference |
| `prompts/narrative_system.txt` | System prompt enforcing grounding rules |

**Key Constraint:** Every claim MUST have evidence_refs (non-empty list). The agent never makes recommendations or evaluates policies.

#### Evals Framework (`/evals/`)
| Validator | Purpose |
|-----------|---------|
| `grounding.py` | Validates all claims reference valid evidence IDs |
| `hallucination.py` | Detects forbidden patterns (recommendations, opinions, severity judgments) |
| `runner.py` | CI-integrated runner (exit 1 on any failure) |

**Forbidden Patterns Detected:**
- Recommendations: "should", "recommend", "best option", "ought to"
- Opinions: "I think", "appears to be", "probably", "likely"
- Severity judgments: "critical", "urgent", "immediately"
- Policy evaluations: "too strict", "too lenient", "should be changed"

---

## Test Coverage

**Total Tests:** 203
**Passing:** 187
**Skipped:** 16 (MCP tests - require `mcp` library)

| Module | Tests | Status |
|--------|-------|--------|
| `/tests/replay/` | 47 | PASS |
| `/tests/coprocessor/` | 42 | PASS |
| `/tests/evals/` | 41 | PASS |
| `/tests/packs/` | 41 | PASS |
| `/tests/mcp_server/` | 16 | SKIP (library not installed) |

---

## Files Created

### New Modules (25 files)
```
/replay/
  __init__.py
  csv_ingestor.py      # CSV ingestion with provenance
  harness.py           # Replay orchestrator
  comparison.py        # Before/after comparison
  metrics.py           # Exception budgets and analytics
  cli.py               # CLI interface

/mcp_server/
  __init__.py
  server.py            # FastMCP server
  tools/__init__.py

/packs/wealth/
  __init__.py
  signal_types.py      # 8 wealth signal types
  policy_templates.py  # 8 wealth policies
  option_templates.py  # Symmetric decision options
  fixtures/scenarios.json  # 7 demo scenarios

/coprocessor/
  __init__.py
  agents/__init__.py
  agents/narrative_agent.py
  schemas/__init__.py
  schemas/narrative.py
  prompts/narrative_system.txt

/evals/
  __init__.py
  runner.py            # CI-gated eval runner
  validators/__init__.py
  validators/grounding.py
  validators/hallucination.py
  datasets/narrative_goldens.json
```

### Test Files (13 files)
```
/tests/
  conftest.py          # Shared fixtures
  replay/
    test_csv_ingestor.py
    test_harness.py
    test_comparison.py
    test_metrics.py
  mcp_server/
    test_server.py
  coprocessor/
    test_schemas.py
    test_narrative_agent.py
  evals/
    test_grounding.py
    test_hallucination.py
    test_runner.py
  packs/
    test_wealth.py
```

### Modified Files
- `README.md` - Updated with Sprint 2 documentation
- `Makefile` - Added replay, mcp, evals commands
- `core/requirements.txt` - Added anthropic dependency

---

## Safety Invariants Maintained

| Invariant | Status |
|-----------|--------|
| LLMs never evaluate policies | ENFORCED |
| All narrative claims reference evidence | ENFORCED (eval-gated) |
| MCP v0 is read-only | ENFORCED (no write tools) |
| Replay is deterministic | ENFORCED (input_hash verification) |
| No recommendations in options | ENFORCED (hallucination detector) |

---

## CLI Commands Added

```bash
# Replay harness
make replay PACK=treasury FROM=2025-01-01 TO=2025-03-31

# MCP server (for Claude Desktop)
make mcp

# Run evaluations (CI gate)
make evals

# Load demo scenarios
make scenarios
```

---

## Known Limitations

1. **MCP Server:** Requires `mcp` library installation (not in default requirements)
2. **NarrativeAgent:** Requires `anthropic` API key for LLM calls
3. **Wealth Pack:** No UI integration yet (backend-only)
4. **Replay CLI:** Database connection required for `run_from_db`

---

## Next Steps (Sprint 3)

- MCP write tools with approval gates + audit events
- IntakeAgent (unstructured → candidate signals)
- Agent tracing viewer
- Expanded eval suites (extraction accuracy + kernel regression)
