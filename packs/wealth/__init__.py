"""
Wealth Pack - Domain configuration for Wealth Management.

Provides signal types, policy templates, option templates, and fixtures
for wealth management governance use cases.

Signal Types (8):
- portfolio_drift - Allocation drifted from target
- rebalancing_required - Rebalancing threshold triggered
- suitability_mismatch - Client risk profile vs holdings
- concentration_breach - Single position concentration
- tax_loss_harvest_opportunity - Tax-loss harvesting signal
- client_cash_withdrawal - Large withdrawal request
- market_correlation_spike - Portfolio correlation risk
- fee_schedule_change - Fee changes affecting client

Policies (8):
- Portfolio Drift Policy
- Rebalancing Policy
- Suitability Policy
- Concentration Policy
- Tax Loss Harvesting Policy
- Withdrawal Policy
- Correlation Risk Policy
- Fee Change Policy
"""

from .signal_types import WEALTH_SIGNAL_TYPES
from .policy_templates import WEALTH_POLICY_TEMPLATES
from .option_templates import WEALTH_OPTION_TEMPLATES

__all__ = [
    "WEALTH_SIGNAL_TYPES",
    "WEALTH_POLICY_TEMPLATES",
    "WEALTH_OPTION_TEMPLATES",
]
