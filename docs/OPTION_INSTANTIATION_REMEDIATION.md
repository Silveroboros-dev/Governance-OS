# Option Instantiation Remediation Plan

## Overview

This document outlines the changes needed to bring the Exception Resolution system into compliance with the Developer Contract for Exception Resolution Instantiation.

---

## Current State vs Required State

### Current Architecture
```
Signal Type → Hard-coded Templates → Options
```

### Required Architecture (per Contract)
```
Exception
  ↓
Relevant policies identified
  ↓
Allowed action types extracted from policies
  ↓
Current system capabilities filtered
  ↓
Action templates instantiated
  ↓
Risks + reversibility attached
  ↓
Options rendered to human
```

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

### 1.4 Update Option Schema

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

### 2.2 Capability Constraints

```python
# core/services/capability_checker.py

class TreasuryCapabilityChecker:
    """
    Treasury capability constraints per Developer Contract §3.2.

    Options must be constrained by:
    - Committed facility limits
    - Undrawn capacity
    - Hedge instrument liquidity
    - Counterparty availability
    - Settlement latency
    """

    def filter_feasible_actions(
        self,
        action_types: Set[str],
        context: Dict
    ) -> Set[str]:
        feasible = set()

        for action_type in action_types:
            if action_type == TreasuryActionType.DRAW_CREDIT_LINE.value:
                # Check undrawn capacity
                if self._has_undrawn_capacity(context):
                    feasible.add(action_type)
            elif action_type == TreasuryActionType.ADJUST_FX_HEDGE.value:
                # Check hedge instrument liquidity
                if self._has_hedge_liquidity(context):
                    feasible.add(action_type)
            # ... etc
            elif action_type == TreasuryActionType.NONE.value:
                # "None" is always feasible
                feasible.add(action_type)

        return feasible


class WealthCapabilityChecker:
    """
    Wealth capability constraints per Developer Contract §4.2.

    Options must be constrained by:
    - Client mandate
    - Suitability profile
    - Liquidity of underlying assets
    - Tax jurisdiction
    - Legal structure (trust, foundation, individual)
    """

    def filter_feasible_actions(
        self,
        action_types: Set[str],
        context: Dict
    ) -> Set[str]:
        feasible = set()

        for action_type in action_types:
            if action_type == WealthActionType.TAX_LOSS_HARVEST.value:
                # Check tax jurisdiction allows it
                if self._tax_harvesting_allowed(context):
                    feasible.add(action_type)
            elif action_type == WealthActionType.REBALANCE_PORTFOLIO.value:
                # Check client mandate permits rebalancing
                if self._rebalancing_permitted(context):
                    feasible.add(action_type)
            # ... etc
            elif action_type in (WealthActionType.NONE.value,
                                  WealthActionType.PAUSE_AUTOMATION.value):
                # Always feasible
                feasible.add(action_type)

        return feasible
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

1. **Capability data sources**: Where do we get real-time capability data (credit facility limits, hedge liquidity)?

2. **Policy authoring**: How do admins specify `allowed_action_types` when creating policies? UI needed?

3. **"No safe action" handling**: Contract says surface "No safe action available" if no policy allows any action. How should UI handle this?

4. **Backward compatibility**: Existing exceptions have options in old format. Migrate or grandfather?

---

## One-Line Rule (For Code Comments)

> **The system may enumerate safe moves, but it must never decide which move to take.**
