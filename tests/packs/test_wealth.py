"""
Tests for Wealth Pack - Wealth management domain configuration.
"""

import pytest
import json
from pathlib import Path


class TestWealthSignalTypes:
    """Tests for wealth signal type definitions."""

    @pytest.fixture
    def signal_types(self):
        """Load wealth signal types."""
        from packs.wealth.signal_types import WEALTH_SIGNAL_TYPES
        return WEALTH_SIGNAL_TYPES

    def test_signal_types_count(self, signal_types):
        """Test that all 8 signal types are defined."""
        assert len(signal_types) == 8

    def test_signal_types_have_required_fields(self, signal_types):
        """Test that each signal type has required fields."""
        required_fields = ["description", "payload_schema", "severity_default"]

        for name, config in signal_types.items():
            for field in required_fields:
                assert field in config, f"Signal type {name} missing field: {field}"

    def test_portfolio_drift_signal(self, signal_types):
        """Test portfolio_drift signal type configuration."""
        assert "portfolio_drift" in signal_types

        sig = signal_types["portfolio_drift"]
        assert "drift_percent" in sig["payload_schema"]
        assert "portfolio_value_usd" in sig["payload_schema"]
        assert sig["severity_default"] in ["low", "medium", "high", "critical"]

    def test_suitability_mismatch_signal(self, signal_types):
        """Test suitability_mismatch signal type configuration."""
        assert "suitability_mismatch" in signal_types

        sig = signal_types["suitability_mismatch"]
        assert "client_risk_score" in sig["payload_schema"]
        assert "portfolio_risk_score" in sig["payload_schema"]
        assert "risk_delta" in sig["payload_schema"]

    def test_concentration_breach_signal(self, signal_types):
        """Test concentration_breach signal type configuration."""
        assert "concentration_breach" in signal_types

        sig = signal_types["concentration_breach"]
        assert "current_weight_percent" in sig["payload_schema"]
        assert "limit_percent" in sig["payload_schema"]

    def test_tax_loss_harvest_signal(self, signal_types):
        """Test tax_loss_harvest_opportunity signal type configuration."""
        assert "tax_loss_harvest_opportunity" in signal_types

        sig = signal_types["tax_loss_harvest_opportunity"]
        assert "unrealized_loss_usd" in sig["payload_schema"]
        assert "estimated_tax_savings_usd" in sig["payload_schema"]

    def test_client_withdrawal_signal(self, signal_types):
        """Test client_cash_withdrawal signal type configuration."""
        assert "client_cash_withdrawal" in signal_types

        sig = signal_types["client_cash_withdrawal"]
        assert "withdrawal_amount_usd" in sig["payload_schema"]
        assert "withdrawal_percent" in sig["payload_schema"]

    def test_all_signal_types_list(self, signal_types):
        """Test all expected signal types are present."""
        expected_types = [
            "portfolio_drift",
            "rebalancing_required",
            "suitability_mismatch",
            "concentration_breach",
            "tax_loss_harvest_opportunity",
            "client_cash_withdrawal",
            "market_correlation_spike",
            "fee_schedule_change",
        ]

        for sig_type in expected_types:
            assert sig_type in signal_types, f"Missing signal type: {sig_type}"


class TestWealthPolicyTemplates:
    """Tests for wealth policy template definitions."""

    @pytest.fixture
    def policy_templates(self):
        """Load wealth policy templates."""
        from packs.wealth.policy_templates import WEALTH_POLICY_TEMPLATES
        return WEALTH_POLICY_TEMPLATES

    def test_policy_templates_count(self, policy_templates):
        """Test that all 8 policies are defined."""
        assert len(policy_templates) == 8

    def test_policy_templates_have_required_fields(self, policy_templates):
        """Test that each policy has required fields."""
        required_fields = ["name", "description", "rule_definition"]

        for name, config in policy_templates.items():
            for field in required_fields:
                assert field in config, f"Policy {name} missing field: {field}"

    def test_policy_rule_definitions_valid(self, policy_templates):
        """Test that rule definitions have valid structure."""
        for name, config in policy_templates.items():
            rule = config["rule_definition"]

            assert "type" in rule, f"Policy {name} missing rule type"
            assert rule["type"] == "threshold_breach", f"Policy {name} has unexpected rule type"
            assert "conditions" in rule, f"Policy {name} missing conditions"
            assert len(rule["conditions"]) > 0, f"Policy {name} has no conditions"

    def test_policy_conditions_have_thresholds(self, policy_templates):
        """Test that all conditions have threshold definitions."""
        for name, config in policy_templates.items():
            for i, condition in enumerate(config["rule_definition"]["conditions"]):
                assert "threshold" in condition, \
                    f"Policy {name} condition {i} missing threshold"
                assert "field" in condition["threshold"], \
                    f"Policy {name} condition {i} threshold missing field"
                assert "operator" in condition["threshold"], \
                    f"Policy {name} condition {i} threshold missing operator"

    def test_portfolio_drift_policy(self, policy_templates):
        """Test portfolio drift policy configuration."""
        assert "portfolio_drift_policy" in policy_templates

        policy = policy_templates["portfolio_drift_policy"]
        assert policy["name"] == "Portfolio Drift Policy"
        assert policy["rule_definition"]["conditions"][0]["signal_type"] == "portfolio_drift"

    def test_suitability_policy(self, policy_templates):
        """Test suitability policy configuration."""
        assert "suitability_policy" in policy_templates

        policy = policy_templates["suitability_policy"]
        assert "suitability" in policy["name"].lower()

    def test_all_policies_list(self, policy_templates):
        """Test all expected policies are present."""
        expected_policies = [
            "portfolio_drift_policy",
            "rebalancing_policy",
            "suitability_policy",
            "concentration_policy",
            "tax_loss_harvesting_policy",
            "withdrawal_policy",
            "correlation_risk_policy",
            "fee_change_policy",
        ]

        for policy_name in expected_policies:
            assert policy_name in policy_templates, f"Missing policy: {policy_name}"


class TestWealthOptionTemplates:
    """Tests for wealth option template definitions."""

    @pytest.fixture
    def option_templates(self):
        """Load wealth option templates."""
        from packs.wealth.option_templates import WEALTH_OPTION_TEMPLATES
        return WEALTH_OPTION_TEMPLATES

    def test_option_templates_count(self, option_templates):
        """Test that options are defined for all signal types."""
        assert len(option_templates) == 8

    def test_option_templates_have_multiple_options(self, option_templates):
        """Test that each signal type has multiple symmetric options."""
        for sig_type, options in option_templates.items():
            assert len(options) >= 2, f"Signal type {sig_type} has fewer than 2 options"
            assert len(options) <= 5, f"Signal type {sig_type} has more than 5 options"

    def test_option_templates_structure(self, option_templates):
        """Test that options have required fields."""
        required_fields = ["label", "description", "implications"]

        for sig_type, options in option_templates.items():
            for i, option in enumerate(options):
                for field in required_fields:
                    assert field in option, \
                        f"Signal type {sig_type} option {i} missing field: {field}"

    def test_options_have_implications(self, option_templates):
        """Test that all options have at least one implication."""
        for sig_type, options in option_templates.items():
            for i, option in enumerate(options):
                assert len(option["implications"]) >= 1, \
                    f"Signal type {sig_type} option {i} has no implications"

    def test_options_are_symmetric(self, option_templates):
        """Test that options don't contain recommendation language."""
        recommendation_words = ["best", "recommended", "optimal", "preferred", "should"]

        for sig_type, options in option_templates.items():
            for i, option in enumerate(options):
                label_lower = option["label"].lower()
                desc_lower = option["description"].lower()

                for word in recommendation_words:
                    assert word not in label_lower, \
                        f"Signal type {sig_type} option {i} label contains '{word}'"
                    assert word not in desc_lower, \
                        f"Signal type {sig_type} option {i} description contains '{word}'"

    def test_portfolio_drift_options(self, option_templates):
        """Test portfolio drift has appropriate options."""
        assert "portfolio_drift" in option_templates

        options = option_templates["portfolio_drift"]
        labels = [o["label"] for o in options]

        # Should have options like rebalance now, schedule, monitor
        assert any("rebalance" in l.lower() for l in labels)

    def test_tax_loss_harvest_options(self, option_templates):
        """Test tax loss harvest has appropriate options."""
        assert "tax_loss_harvest_opportunity" in option_templates

        options = option_templates["tax_loss_harvest_opportunity"]
        labels = [o["label"] for o in options]

        # Should have execute and decline options
        assert any("execute" in l.lower() or "harvest" in l.lower() for l in labels)
        assert any("decline" in l.lower() or "defer" in l.lower() for l in labels)


class TestWealthScenarios:
    """Tests for wealth demo scenarios."""

    @pytest.fixture
    def scenarios_path(self):
        """Get path to scenarios file."""
        return Path(__file__).parent.parent.parent / "packs" / "wealth" / "fixtures" / "scenarios.json"

    @pytest.fixture
    def scenarios(self, scenarios_path):
        """Load scenarios from JSON file."""
        with open(scenarios_path) as f:
            return json.load(f)

    def test_scenarios_file_exists(self, scenarios_path):
        """Test that scenarios file exists."""
        assert scenarios_path.exists(), "Wealth scenarios file not found"

    def test_scenarios_valid_json(self, scenarios):
        """Test that scenarios file is valid JSON."""
        assert "scenarios" in scenarios
        assert isinstance(scenarios["scenarios"], list)

    def test_scenarios_count(self, scenarios):
        """Test that we have expected number of scenarios."""
        assert len(scenarios["scenarios"]) >= 7

    def test_scenarios_have_required_fields(self, scenarios):
        """Test that scenarios have required fields."""
        required_fields = ["id", "name", "description", "signals", "expected_severity"]

        for scenario in scenarios["scenarios"]:
            for field in required_fields:
                assert field in scenario, \
                    f"Scenario {scenario.get('id')} missing field: {field}"

    def test_scenarios_have_signals(self, scenarios):
        """Test that each scenario has at least one signal."""
        for scenario in scenarios["scenarios"]:
            assert len(scenario["signals"]) >= 1, \
                f"Scenario {scenario['id']} has no signals"

    def test_scenario_signals_valid(self, scenarios):
        """Test that scenario signals have valid structure."""
        required_signal_fields = ["signal_type", "source", "payload"]

        for scenario in scenarios["scenarios"]:
            for i, signal in enumerate(scenario["signals"]):
                for field in required_signal_fields:
                    assert field in signal, \
                        f"Scenario {scenario['id']} signal {i} missing field: {field}"

    def test_scenario_severities_valid(self, scenarios):
        """Test that expected severities are valid values."""
        valid_severities = ["low", "medium", "high", "critical"]

        for scenario in scenarios["scenarios"]:
            assert scenario["expected_severity"] in valid_severities, \
                f"Scenario {scenario['id']} has invalid severity: {scenario['expected_severity']}"

    def test_scenarios_have_narratives(self, scenarios):
        """Test that scenarios have narrative descriptions."""
        for scenario in scenarios["scenarios"]:
            assert "narrative" in scenario, \
                f"Scenario {scenario['id']} missing narrative"
            assert len(scenario["narrative"]) > 50, \
                f"Scenario {scenario['id']} narrative too short"


class TestWealthPackModule:
    """Tests for wealth pack module imports."""

    def test_module_imports(self):
        """Test that wealth pack module imports correctly."""
        from packs.wealth import (
            WEALTH_SIGNAL_TYPES,
            WEALTH_POLICY_TEMPLATES,
            WEALTH_OPTION_TEMPLATES,
        )

        assert WEALTH_SIGNAL_TYPES is not None
        assert WEALTH_POLICY_TEMPLATES is not None
        assert WEALTH_OPTION_TEMPLATES is not None

    def test_signal_policy_alignment(self):
        """Test that policies reference valid signal types."""
        from packs.wealth.signal_types import WEALTH_SIGNAL_TYPES
        from packs.wealth.policy_templates import WEALTH_POLICY_TEMPLATES

        signal_types = set(WEALTH_SIGNAL_TYPES.keys())

        for policy_name, policy in WEALTH_POLICY_TEMPLATES.items():
            for condition in policy["rule_definition"]["conditions"]:
                sig_type = condition["signal_type"]
                assert sig_type in signal_types, \
                    f"Policy {policy_name} references unknown signal type: {sig_type}"

    def test_option_signal_alignment(self):
        """Test that option templates cover all signal types."""
        from packs.wealth.signal_types import WEALTH_SIGNAL_TYPES
        from packs.wealth.option_templates import WEALTH_OPTION_TEMPLATES

        signal_types = set(WEALTH_SIGNAL_TYPES.keys())
        option_types = set(WEALTH_OPTION_TEMPLATES.keys())

        assert signal_types == option_types, \
            f"Signal types and option templates don't match. " \
            f"Missing in options: {signal_types - option_types}. " \
            f"Extra in options: {option_types - signal_types}"
