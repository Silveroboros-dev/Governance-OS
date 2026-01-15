# Option Instantiation Remediation Plan

## Overview

This document outlines the changes needed to bring the Exception Resolution system into compliance with the Developer Contract for Exception Resolution Instantiation.

**Critical Constraint:** All changes must preserve kernel determinism (same inputs → same outputs, replayable).

---

## Current State vs Required State

### Current Architecture
```
Signal Type → Hard-coded Templates → Options
```

### Required Architecture (per Contract + Determinism Preservation)
```
Signal Ingestion
  ↓
Capability snapshot captured (frozen at ingestion time)
  ↓
Exception raised
  ↓
Relevant policies identified
  ↓
Allowed action types extracted from policies
  ↓
Feasibility filtered using FROZEN capability snapshot
  ↓
Action templates instantiated
  ↓
Risks + reversibility attached
  ↓
Options rendered to human
```

### Determinism Guarantee

The capability filtering step uses data captured at signal ingestion, NOT live queries:

| Data Source | Deterministic? | Used In This Plan |
|-------------|----------------|-------------------|
| Live API query to credit facility | ❌ No | ❌ Not used |
| Snapshot stored in Signal.payload | ✅ Yes | ✅ Used |
| Snapshot stored in Evaluation.context | ✅ Yes | ✅ Used |

This ensures replay produces identical options regardless of when it runs.

---

## Phase 1: Data Model Changes

### 1.1 Define Action Type Enums

Create strict action type enums per domain:

```python
# core/domain/action_types.py

class TreasuryActionType(str, Enum):
    """Treasury-allowed action classes per Developer Contract §3.1"""
    DRAW_CREDIT_LINE = "draw_credit_line"
    REPAY_CREDIT_LINE = "repay_credit_line"
    ADJUST_FX_HEDGE = "adjust_fx_hedge"
    ADJUST_IR_HEDGE = "adjust_ir_hedge"
    FREEZE_NONCRITICAL_OUTFLOWS = "freeze_noncritical_outflows"
    REALLOCATE_INTERNAL_CASH = "reallocate_internal_cash"
    NONE = "none"  # Mandatory "do nothing" option

class WealthActionType(str, Enum):
    """Wealth-allowed action classes per Developer Contract §4.1"""
    REBALANCE_PORTFOLIO = "rebalance_portfolio"
    ADJUST_ASSET_ALLOCATION = "adjust_asset_allocation"
    TAX_LOSS_HARVEST = "tax_loss_harvest"
    CHANGE_DRAWDOWN_RATE = "change_drawdown_rate"
    RESTRUCTURE_HOLDINGS = "restructure_holdings"
    PAUSE_AUTOMATION = "pause_automation"  # Mandatory per §4.4
    NONE = "none"  # Mandatory "do nothing" option
```

### 1.2 Add Reversibility Enum

```python
# core/domain/action_types.py

class Reversibility(str, Enum):
    """Reversibility classes per Developer Contract §I6"""
    REVERSIBLE = "reversible"
    COSTLY_TO_REVERSE = "costly_to_reverse"
    IRREVERSIBLE = "irreversible"
```

### 1.3 Update Policy Model

Add `allowed_action_types` to PolicyVersion:

```python
# In PolicyVersion model
allowed_action_types = Column(ARRAY(String), nullable=False)
# e.g., ["draw_credit_line", "adjust_fx_hedge", "none"]
```

### 1.4 Capability Snapshot Schema (NEW - Determinism Critical)

Capability data must be captured at signal ingestion time to preserve replay determinism:

```python
# core/schemas/capability_snapshot.py

class TreasuryCapabilitySnapshot(BaseModel):
    """
    Point-in-time snapshot of treasury system capabilities.

    CRITICAL: This data is frozen at signal ingestion time.
    Option instantiation reads from this snapshot, NEVER from live systems.
    """
    snapshot_at: datetime

    # Credit facilities
    credit_facilities: List[CreditFacilitySnapshot] = []
    total_committed: Decimal = Decimal("0")
    total_drawn: Decimal = Decimal("0")
    total_undrawn: Decimal = Decimal("0")

    # Hedging capacity
    fx_hedge_capacity_available: bool = True
    ir_hedge_capacity_available: bool = True

    # Counterparty status
    counterparty_availability: Dict[str, bool] = {}

    # Settlement windows
    next_settlement_window: Optional[datetime] = None


class CreditFacilitySnapshot(BaseModel):
    """Individual credit facility state at snapshot time."""
    facility_id: str
    facility_name: str
    committed_amount: Decimal
    drawn_amount: Decimal
    available_amount: Decimal
    is_available: bool  # False if frozen, covenant breach, etc.


class WealthCapabilitySnapshot(BaseModel):
    """
    Point-in-time snapshot of wealth management capabilities.

    CRITICAL: Frozen at signal ingestion time for determinism.
    """
    snapshot_at: datetime

    # Client mandate constraints
    client_id: str
    mandate_permits_rebalancing: bool = True
    mandate_permits_tax_harvesting: bool = True
    mandate_permits_drawdown_changes: bool = True

    # Suitability
    suitability_profile: str  # "conservative", "moderate", "aggressive"

    # Tax jurisdiction
    tax_jurisdiction: str
    tax_harvesting_available: bool = True

    # Legal structure
    legal_structure: str  # "individual", "trust", "foundation", "corporate"
    structure_permits_restructuring: bool = True

    # Asset liquidity
    illiquid_asset_percentage: Decimal = Decimal("0")
```

### 1.5 Signal Payload Extension

Signals must include capability snapshots:

```python
# In Signal model - payload structure
{
    "type": "position_limit_breach",
    "value": 47200000,
    "threshold": 37200000,
    # ... existing fields ...

    # NEW: Capability snapshot (frozen at ingestion)
    "capability_snapshot": {
        "snapshot_at": "2026-01-15T10:30:00Z",
        "credit_facilities": [...],
        "total_undrawn": 5000000,
        "fx_hedge_capacity_available": true,
        # ... etc
    }
}
```

### 1.6 Update Option Schema

```python
# core/schemas/option.py

class ResolutionOption(BaseModel):
    """Resolution option per Developer Contract requirements"""
    id: str
    action_type: str  # Must be from domain's allowed action types
    label: str
    description: str

    # Required risk declarations (§3.3 Treasury, §4.3 Wealth)
    reversibility: Reversibility  # §I6 - Mandatory

    # Treasury-specific (§3.3)
    liquidity_impact: Optional[str] = None
    counterparty_risk: Optional[str] = None
    covenant_optics: Optional[str] = None

    # Wealth-specific (§4.3)
    suitability_risk: Optional[str] = None
    tax_impact: Optional[str] = None
    behavioral_risk: Optional[str] = None  # Mandatory for Wealth

    # General
    implications: List[str] = []
    policy_references: List[str]  # §I2 - Must reference allowing policies
```

---

## Phase 2: Option Instantiation Pipeline

### 2.1 New Pipeline Implementation

```python
# core/services/option_instantiator.py

class OptionInstantiator:
    """
    Implements the canonical option instantiation pipeline.

    The system may enumerate safe moves, but it must never decide which move to take.
    """

    def instantiate_options(
        self,
        exception: Exception,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> List[ResolutionOption]:
        """
        Execute the canonical pipeline per Developer Contract §2.

        Steps (none may be skipped or merged):
        1. Identify relevant policies
        2. Extract allowed action types
        3. Filter by current system capabilities
        4. Instantiate action templates
        5. Attach risks + reversibility
        6. Return options for human selection
        """
        pack = policy_version.policy.pack

        # Step 1: Identify relevant policies
        relevant_policies = self._get_relevant_policies(evaluation, policy_version)

        # Step 2: Extract allowed action types
        allowed_types = self._extract_allowed_action_types(relevant_policies, pack)

        # Step 3: Filter by system capabilities
        feasible_types = self._filter_by_capabilities(allowed_types, evaluation)

        # Step 4: Instantiate templates
        options = self._instantiate_templates(feasible_types, pack, evaluation)

        # Step 5: Attach risks + reversibility
        options = self._attach_risk_declarations(options, pack, evaluation)

        # Invariant checks
        self._validate_invariants(options, pack)

        return options

    def _extract_allowed_action_types(
        self,
        policies: List[PolicyVersion],
        pack: str
    ) -> Set[str]:
        """Extract union of allowed action types from all relevant policies."""
        allowed = set()
        for policy in policies:
            allowed.update(policy.allowed_action_types or [])

        # §I3: "Do Nothing" is mandatory
        if pack == "treasury":
            allowed.add(TreasuryActionType.NONE.value)
        elif pack == "wealth":
            allowed.add(WealthActionType.NONE.value)
            # §4.4: "Pause Automation" is mandatory for Wealth
            allowed.add(WealthActionType.PAUSE_AUTOMATION.value)

        return allowed

    def _validate_invariants(self, options: List[ResolutionOption], pack: str):
        """Validate all contract invariants. Raises if violated."""

        # §I2: Every option must reference at least one policy
        for opt in options:
            if not opt.policy_references:
                raise ContractViolation(f"Option '{opt.id}' has no policy reference (§I2)")

        # §I3: "Do Nothing" must be present
        has_none = any(opt.action_type in ("none", "NONE") for opt in options)
        if not has_none:
            raise ContractViolation("Missing 'no action' option (§I3)")

        # §I6: All options must have reversibility
        for opt in options:
            if not opt.reversibility:
                raise ContractViolation(f"Option '{opt.id}' missing reversibility (§I6)")

        # §4.4: Wealth must have "Pause Automation"
        if pack == "wealth":
            has_pause = any(
                opt.action_type == WealthActionType.PAUSE_AUTOMATION.value
                for opt in options
            )
            if not has_pause:
                raise ContractViolation("Wealth missing 'Pause Automation' option (§4.4)")

        # Domain action class validation
        valid_types = self._get_valid_action_types(pack)
        for opt in options:
            if opt.action_type not in valid_types:
                raise ContractViolation(
                    f"Invalid action type '{opt.action_type}' for {pack} (§3.1/§4.1)"
                )
```

### 2.2 Capability Constraints (Deterministic - Snapshot-Based)

**CRITICAL:** Capability checkers read from frozen snapshots, never live systems.

```python
# core/services/capability_checker.py

class TreasuryCapabilityChecker:
    """
    Treasury capability constraints per Developer Contract §3.2.

    DETERMINISM GUARANTEE: All checks read from TreasuryCapabilitySnapshot
    stored in signal.payload["capability_snapshot"], NOT live API calls.

    Options constrained by (from snapshot):
    - Committed facility limits
    - Undrawn capacity
    - Hedge instrument liquidity
    - Counterparty availability
    - Settlement latency
    """

    def filter_feasible_actions(
        self,
        action_types: Set[str],
        snapshot: TreasuryCapabilitySnapshot  # ← Frozen data, not live!
    ) -> Set[str]:
        """
        Filter actions by capability snapshot.

        Args:
            action_types: Candidate action types from policy
            snapshot: FROZEN capability data from signal ingestion time

        Returns:
            Feasible subset of action types
        """
        feasible = set()

        for action_type in action_types:
            if action_type == TreasuryActionType.DRAW_CREDIT_LINE.value:
                # Check undrawn capacity FROM SNAPSHOT
                if snapshot.total_undrawn > 0:
                    feasible.add(action_type)
            elif action_type == TreasuryActionType.ADJUST_FX_HEDGE.value:
                # Check hedge availability FROM SNAPSHOT
                if snapshot.fx_hedge_capacity_available:
                    feasible.add(action_type)
            elif action_type == TreasuryActionType.ADJUST_IR_HEDGE.value:
                if snapshot.ir_hedge_capacity_available:
                    feasible.add(action_type)
            elif action_type == TreasuryActionType.NONE.value:
                # "None" is always feasible
                feasible.add(action_type)
            else:
                # Default: assume feasible if not explicitly constrained
                feasible.add(action_type)

        return feasible


class WealthCapabilityChecker:
    """
    Wealth capability constraints per Developer Contract §4.2.

    DETERMINISM GUARANTEE: All checks read from WealthCapabilitySnapshot
    stored in signal.payload["capability_snapshot"], NOT live API calls.

    Options constrained by (from snapshot):
    - Client mandate
    - Suitability profile
    - Liquidity of underlying assets
    - Tax jurisdiction
    - Legal structure (trust, foundation, individual)
    """

    def filter_feasible_actions(
        self,
        action_types: Set[str],
        snapshot: WealthCapabilitySnapshot  # ← Frozen data, not live!
    ) -> Set[str]:
        """
        Filter actions by capability snapshot.

        Args:
            action_types: Candidate action types from policy
            snapshot: FROZEN capability data from signal ingestion time

        Returns:
            Feasible subset of action types
        """
        feasible = set()

        for action_type in action_types:
            if action_type == WealthActionType.TAX_LOSS_HARVEST.value:
                # Check tax jurisdiction FROM SNAPSHOT
                if snapshot.tax_harvesting_available:
                    feasible.add(action_type)
            elif action_type == WealthActionType.REBALANCE_PORTFOLIO.value:
                # Check mandate FROM SNAPSHOT
                if snapshot.mandate_permits_rebalancing:
                    feasible.add(action_type)
            elif action_type == WealthActionType.CHANGE_DRAWDOWN_RATE.value:
                if snapshot.mandate_permits_drawdown_changes:
                    feasible.add(action_type)
            elif action_type == WealthActionType.RESTRUCTURE_HOLDINGS.value:
                if snapshot.structure_permits_restructuring:
                    feasible.add(action_type)
            elif action_type in (WealthActionType.NONE.value,
                                  WealthActionType.PAUSE_AUTOMATION.value):
                # Always feasible (mandatory per contract)
                feasible.add(action_type)
            else:
                # Default: assume feasible
                feasible.add(action_type)

        return feasible
```

### 2.3 Pipeline Update - Snapshot Extraction

The option instantiator extracts the snapshot from the signal:

```python
# In OptionInstantiator.instantiate_options()

def _get_capability_snapshot(self, evaluation: Evaluation, pack: str):
    """
    Extract frozen capability snapshot from signal payload.

    CRITICAL: This is the ONLY source of capability data.
    Never call external APIs here.
    """
    # Get signals from evaluation
    signals = self._get_evaluation_signals(evaluation)

    for signal in signals:
        snapshot_data = signal.payload.get("capability_snapshot")
        if snapshot_data:
            if pack == "treasury":
                return TreasuryCapabilitySnapshot(**snapshot_data)
            elif pack == "wealth":
                return WealthCapabilitySnapshot(**snapshot_data)

    # No snapshot = all actions assumed feasible (conservative default)
    return None

def _filter_by_capabilities(
    self,
    allowed_types: Set[str],
    evaluation: Evaluation,
    pack: str
) -> Set[str]:
    """Filter by capabilities using FROZEN snapshot."""
    snapshot = self._get_capability_snapshot(evaluation, pack)

    if snapshot is None:
        # No snapshot available - return all types (no filtering)
        # This maintains backward compatibility
        return allowed_types

    if pack == "treasury":
        checker = TreasuryCapabilityChecker()
        return checker.filter_feasible_actions(allowed_types, snapshot)
    elif pack == "wealth":
        checker = WealthCapabilityChecker()
        return checker.filter_feasible_actions(allowed_types, snapshot)

    return allowed_types
```

---

## Phase 3: Template Restructuring

### 3.1 Treasury Templates (Revised)

```python
# packs/treasury/action_templates.py

TREASURY_ACTION_TEMPLATES = {
    TreasuryActionType.DRAW_CREDIT_LINE: {
        "label": "Draw on Credit Facility",
        "description": "Access existing credit line for liquidity",
        "reversibility": Reversibility.REVERSIBLE,
        "liquidity_impact": "Immediate improvement",
        "counterparty_risk": "Increases lender exposure",
        "covenant_optics": "May affect covenant ratios",
    },
    TreasuryActionType.ADJUST_FX_HEDGE: {
        "label": "Adjust FX Hedge",
        "description": "Modify foreign exchange hedging position",
        "reversibility": Reversibility.COSTLY_TO_REVERSE,
        "liquidity_impact": "Margin requirements may change",
        "counterparty_risk": "Counterparty exposure adjustment",
        "covenant_optics": "Neutral",
    },
    TreasuryActionType.NONE: {
        "label": "No Action",
        "description": "Accept current state and continue monitoring",
        "reversibility": Reversibility.REVERSIBLE,
        "liquidity_impact": "No change",
        "counterparty_risk": "No change",
        "covenant_optics": "No change",
        "risk_acceptance_required": True,
    },
    # ... all 7 action types
}
```

### 3.2 Wealth Templates (Revised)

```python
# packs/wealth/action_templates.py

WEALTH_ACTION_TEMPLATES = {
    WealthActionType.REBALANCE_PORTFOLIO: {
        "label": "Rebalance Portfolio",
        "description": "Execute trades to return to target allocation",
        "reversibility": Reversibility.COSTLY_TO_REVERSE,
        "suitability_risk": "None if within mandate",
        "tax_impact": "Potential realized gains/losses",
        "behavioral_risk": "Client may question trades",
    },
    WealthActionType.PAUSE_AUTOMATION: {
        "label": "Pause Automation",
        "description": "Suspend automated processes pending review",
        "reversibility": Reversibility.REVERSIBLE,
        "suitability_risk": "None",
        "tax_impact": "None",
        "behavioral_risk": "Client may expect continued automation",
    },
    WealthActionType.NONE: {
        "label": "No Action",
        "description": "Accept current state with documented rationale",
        "reversibility": Reversibility.REVERSIBLE,
        "suitability_risk": "Depends on exception context",
        "tax_impact": "None",
        "behavioral_risk": "Client expects advisory action",
        "risk_acceptance_required": True,
    },
    # ... all 7 action types
}
```

---

## Phase 4: Policy Migration

### 4.1 Add allowed_action_types to Existing Policies

```sql
-- Migration: Add allowed_action_types column
ALTER TABLE policy_versions ADD COLUMN allowed_action_types TEXT[] NOT NULL DEFAULT '{}';

-- Update Treasury policies
UPDATE policy_versions pv
SET allowed_action_types = CASE
    WHEN p.name = 'Liquidity Management Policy'
        THEN ARRAY['draw_credit_line', 'reallocate_internal_cash', 'freeze_noncritical_outflows', 'none']
    WHEN p.name = 'FX Exposure Policy'
        THEN ARRAY['adjust_fx_hedge', 'none']
    WHEN p.name = 'Position Limit Policy'
        THEN ARRAY['none']  -- Only escalation, no direct actions
    -- ... etc
    ELSE ARRAY['none']
END
FROM policies p
WHERE pv.policy_id = p.id AND p.pack = 'treasury';
```

### 4.2 Validation at Policy Creation

```python
# core/services/policy_engine.py

def create_policy_version(self, ..., allowed_action_types: List[str]):
    """Create policy version with action type validation."""
    pack = policy.pack
    valid_types = get_valid_action_types(pack)

    for action_type in allowed_action_types:
        if action_type not in valid_types:
            raise ValueError(
                f"Invalid action type '{action_type}' for {pack}. "
                f"Allowed: {valid_types}"
            )

    # Proceed with creation
```

---

## Phase 5: Testing Requirements

### 5.1 Required Tests (Blocking per Contract §6)

```python
# core/tests/test_option_contract.py

class TestOptionContract:
    """Tests per Developer Contract §6 - all blocking"""

    def test_option_requires_policy_reference(self):
        """§I2: Option exists only if policy allows it"""
        # Every option must have non-empty policy_references

    def test_no_action_always_present(self):
        """§I3: 'No action' option always present"""
        # For every exception, options must include action_type='none'

    def test_reversibility_declared(self):
        """§I6: Reversibility declared on every option"""
        # No option may have reversibility=None

    def test_treasury_action_classes_valid(self):
        """§3.1: Treasury options only use allowed action classes"""
        # All treasury options must use TreasuryActionType values

    def test_wealth_action_classes_valid(self):
        """§4.1: Wealth options only use allowed action classes"""
        # All wealth options must use WealthActionType values

    def test_wealth_has_pause_automation(self):
        """§4.4: Every Wealth exception has 'Pause Automation'"""

    def test_no_recommendation_metadata(self):
        """§I4: No ranking or recommendation fields"""
        # Options must not have 'recommended', 'score', 'rank' fields

    def test_no_cross_domain_sharing(self):
        """§5: No shared options between domains"""
        # Treasury and Wealth option sets must be disjoint

    def test_capability_constraints_enforced(self):
        """§3.2/§4.2: Options filtered by system capabilities"""
```

### 5.2 Determinism Tests (Kernel Integrity - CRITICAL)

```python
# core/tests/test_option_determinism.py

class TestOptionDeterminism:
    """
    Tests ensuring option instantiation remains deterministic.

    CRITICAL: These tests protect kernel integrity.
    Failure means replay will produce different results.
    """

    def test_same_inputs_same_options(self):
        """
        Given identical evaluation + policy + snapshot,
        option instantiation MUST produce identical options.
        """
        evaluation = create_test_evaluation()
        policy = create_test_policy()

        # Run instantiation twice
        options_1 = instantiator.instantiate_options(evaluation, policy)
        options_2 = instantiator.instantiate_options(evaluation, policy)

        # Must be identical (order and content)
        assert options_1 == options_2

    def test_options_depend_only_on_snapshot_not_time(self):
        """
        Options must be independent of wall-clock time.
        Only the frozen snapshot matters.
        """
        # Create signal with snapshot at T0
        signal = create_signal_with_snapshot(
            snapshot_at=datetime(2026, 1, 1),
            total_undrawn=1000000
        )

        # Evaluate at T1 (different wall-clock time)
        with freeze_time("2026-06-15"):
            options = instantiator.instantiate_options(...)

        # Evaluate again at T2
        with freeze_time("2026-12-31"):
            options_later = instantiator.instantiate_options(...)

        # Must produce same options despite different evaluation times
        assert options == options_later

    def test_no_external_api_calls_during_instantiation(self):
        """
        Option instantiation must NOT make external API calls.
        All data comes from frozen snapshot.
        """
        with mock.patch('requests.get') as mock_get:
            with mock.patch('requests.post') as mock_post:
                instantiator.instantiate_options(...)

                # No HTTP calls should have been made
                mock_get.assert_not_called()
                mock_post.assert_not_called()

    def test_replay_produces_identical_options(self):
        """
        Full replay test: same signal + policy = same options.
        """
        # Original run
        signal = ingest_signal(signal_data)
        evaluation = evaluate(signal, policy)
        exception = raise_exception(evaluation)
        original_options = exception.options

        # Replay from stored data
        replayed_signal = load_signal(signal.id)
        replayed_eval = evaluate(replayed_signal, policy)
        replayed_exc = raise_exception(replayed_eval)
        replayed_options = replayed_exc.options

        assert original_options == replayed_options

    def test_capability_checker_uses_only_snapshot(self):
        """
        Capability checker must use snapshot parameter,
        not access any external state.
        """
        checker = TreasuryCapabilityChecker()

        # Create snapshot with specific values
        snapshot = TreasuryCapabilitySnapshot(
            snapshot_at=datetime(2026, 1, 15),
            total_undrawn=Decimal("5000000"),
            fx_hedge_capacity_available=True
        )

        # Filter actions
        result = checker.filter_feasible_actions(
            {"draw_credit_line", "adjust_fx_hedge", "none"},
            snapshot
        )

        # Should include draw_credit_line (undrawn > 0)
        assert "draw_credit_line" in result

        # Now with zero undrawn
        snapshot_empty = TreasuryCapabilitySnapshot(
            snapshot_at=datetime(2026, 1, 15),
            total_undrawn=Decimal("0"),
            fx_hedge_capacity_available=True
        )

        result_empty = checker.filter_feasible_actions(
            {"draw_credit_line", "adjust_fx_hedge", "none"},
            snapshot_empty
        )

        # Should NOT include draw_credit_line
        assert "draw_credit_line" not in result_empty
        # But should still have none (always feasible)
        assert "none" in result_empty
```

---

## Phase 6: Migration Strategy

### Step 1: Add New Models (Non-Breaking)
- Add action type enums
- Add reversibility enum
- Add `allowed_action_types` column to policy_versions (nullable initially)

### Step 2: Dual-Path Implementation
- Create new `OptionInstantiator` alongside existing `_generate_options`
- Feature flag to switch between old and new

### Step 3: Migrate Policies
- Populate `allowed_action_types` for all existing policies
- Make column non-nullable

### Step 4: Migrate Templates
- Convert existing templates to new structure
- Add missing fields (reversibility, risk declarations)

### Step 5: Switch to New Pipeline
- Enable new `OptionInstantiator`
- Remove old template system

### Step 6: Add Blocking Tests
- Enable test suite per §6
- Merge blocked on any failure

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1: Data Models | Small |
| Phase 2: Pipeline | Medium |
| Phase 3: Templates | Medium |
| Phase 4: Migration | Small |
| Phase 5: Tests | Medium |
| Phase 6: Rollout | Small |

---

## Open Questions

1. ~~**Capability data sources**: Where do we get real-time capability data (credit facility limits, hedge liquidity)?~~
   **RESOLVED:** Capability data is captured at signal ingestion time and frozen in `signal.payload.capability_snapshot`. The snapshot is populated by the signal ingestion layer (connectors in Sprint 4). For now, signals without snapshots assume all actions feasible.

2. **Policy authoring**: How do admins specify `allowed_action_types` when creating policies? UI needed?

3. **"No safe action" handling**: Contract says surface "No safe action available" if no policy allows any action. How should UI handle this?

4. **Backward compatibility**: Existing exceptions have options in old format. Migrate or grandfather?

5. **Snapshot enrichment**: Who is responsible for populating capability snapshots in signals?
   - Option A: Signal source system includes snapshot
   - Option B: Ingestion layer enriches signals with snapshot from separate API
   - Option C: Connectors (Sprint 4) handle snapshot capture

---

## Determinism Guarantee Summary

This remediation plan preserves kernel integrity through:

| Component | Determinism Approach |
|-----------|---------------------|
| Policy → Action Types | Static mapping in `allowed_action_types` column |
| Capability Filtering | Reads from frozen `capability_snapshot` in signal |
| Template Instantiation | Pure function of action type + pack |
| Risk Attachment | Static templates per action type |

**Anti-patterns avoided:**
- ❌ Live API calls during option instantiation
- ❌ Wall-clock time dependencies
- ❌ Database queries for external state
- ❌ Random or non-deterministic ordering

**Replay guarantee:** Given the same `Signal`, `PolicyVersion`, and `Evaluation`, option instantiation will always produce identical `ResolutionOption[]`.

---

## One-Line Rule (For Code Comments)

> **The system may enumerate safe moves, but it must never decide which move to take.**

> **Options are deterministic: same inputs, same outputs, always replayable.**
