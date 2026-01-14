"""
Treasury Pack - Decision Option Templates.

Defines symmetric decision options (NO RECOMMENDATIONS!).
"""

TREASURY_OPTION_TEMPLATES = {
    "position_limit_breach": [
        {
            "id": "approve_temporary_increase",
            "label": "Approve Temporary Increase",
            "description": "Allow position to remain above limit for defined period",
            "implications": [
                "Increased market risk exposure",
                "Requires monitoring for duration",
                "May need board notification if critical"
            ]
        },
        {
            "id": "immediate_reduction",
            "label": "Require Immediate Reduction",
            "description": "Mandate position reduction to within limits",
            "implications": [
                "May incur trading costs",
                "Reduces risk exposure",
                "Could impact market execution"
            ]
        },
        {
            "id": "escalate_to_cfo",
            "label": "Escalate to CFO",
            "description": "Elevate decision to CFO for review",
            "implications": [
                "Delays resolution",
                "Higher-level accountability",
                "Appropriate for critical severity"
            ]
        },
    ],
    "market_volatility_spike": [
        {
            "id": "maintain_positions",
            "label": "Maintain Current Positions",
            "description": "No action; continue monitoring",
            "implications": [
                "Accepts current risk profile",
                "Volatility may increase further",
            ]
        },
        {
            "id": "reduce_exposure",
            "label": "Reduce Exposure",
            "description": "Decrease positions in affected assets",
            "implications": [
                "Lowers risk",
                "May incur costs",
                "Potential opportunity cost",
            ]
        },
        {
            "id": "activate_hedges",
            "label": "Activate Hedging Strategies",
            "description": "Deploy pre-approved hedging instruments",
            "implications": [
                "Protects downside",
                "Costs premium",
                "Limits upside",
            ]
        },
    ],
    "counterparty_credit_downgrade": [
        {
            "id": "maintain_relationship",
            "label": "Maintain Relationship",
            "description": "Continue with current exposure levels",
            "implications": [
                "Preserves business relationship",
                "Elevated credit risk",
                "Requires enhanced monitoring"
            ]
        },
        {
            "id": "reduce_exposure",
            "label": "Reduce Exposure",
            "description": "Decrease exposure to counterparty",
            "implications": [
                "Lowers credit risk",
                "May impact business relationship",
                "Operational complexity"
            ]
        },
        {
            "id": "exit_relationship",
            "label": "Exit Relationship",
            "description": "Wind down all exposure to counterparty",
            "implications": [
                "Eliminates credit risk",
                "Loss of business partner",
                "Potential market impact"
            ]
        },
    ],
    "liquidity_threshold_breach": [
        {
            "id": "liquidate_secondary_assets",
            "label": "Liquidate Secondary Assets",
            "description": "Sell less critical assets to restore liquidity",
            "implications": [
                "Immediate liquidity improvement",
                "Potential loss on forced sales",
                "Reduces overall portfolio"
            ]
        },
        {
            "id": "draw_credit_facility",
            "label": "Draw on Credit Facility",
            "description": "Access existing credit line for liquidity",
            "implications": [
                "Quick liquidity access",
                "Increases debt obligations",
                "May affect covenant ratios"
            ]
        },
        {
            "id": "request_temporary_waiver",
            "label": "Request Policy Waiver",
            "description": "Seek temporary waiver on liquidity requirements",
            "implications": [
                "No immediate action required",
                "Requires board/committee approval",
                "Time-limited relief"
            ]
        },
    ],
    "fx_exposure_breach": [
        {
            "id": "execute_spot_hedge",
            "label": "Execute Spot Hedge",
            "description": "Immediately hedge excess FX exposure",
            "implications": [
                "Immediate risk reduction",
                "Transaction costs",
                "Locks in current rates"
            ]
        },
        {
            "id": "forward_contract",
            "label": "Enter Forward Contract",
            "description": "Hedge exposure with forward contract",
            "implications": [
                "Deferred settlement",
                "Rate certainty for future",
                "Counterparty exposure"
            ]
        },
        {
            "id": "approve_temporary_limit",
            "label": "Approve Temporary Limit Increase",
            "description": "Temporarily increase FX exposure limit",
            "implications": [
                "Maintains flexibility",
                "Continued currency risk",
                "Requires limit reset date"
            ]
        },
    ],
    "cash_forecast_variance": [
        {
            "id": "investigate_variance",
            "label": "Investigate Root Cause",
            "description": "Conduct detailed analysis of variance drivers",
            "implications": [
                "Delays corrective action",
                "Better informed decisions",
                "Process improvement opportunity"
            ]
        },
        {
            "id": "adjust_forecast_model",
            "label": "Adjust Forecast Model",
            "description": "Update forecasting methodology based on variance",
            "implications": [
                "Improved future accuracy",
                "May require system changes",
                "Training needs"
            ]
        },
        {
            "id": "initiate_cash_sweep",
            "label": "Initiate Emergency Cash Sweep",
            "description": "Transfer funds from secondary accounts",
            "implications": [
                "Immediate cash improvement",
                "Cross-account dependencies",
                "May affect other operations"
            ]
        },
    ],
    "covenant_breach": [
        {
            "id": "negotiate_waiver",
            "label": "Negotiate Lender Waiver",
            "description": "Request temporary waiver from covenant",
            "implications": [
                "Preserves banking relationship",
                "May incur waiver fees",
                "Requires lender cooperation"
            ]
        },
        {
            "id": "accelerate_debt_paydown",
            "label": "Accelerate Debt Paydown",
            "description": "Make additional principal payments to improve ratio",
            "implications": [
                "Uses available cash",
                "Improves covenant ratio",
                "Reduces future flexibility"
            ]
        },
        {
            "id": "refinance_facility",
            "label": "Explore Refinancing",
            "description": "Seek new facility with different covenant terms",
            "implications": [
                "Potential better terms",
                "Time-consuming process",
                "Market rate exposure"
            ]
        },
    ],
    "settlement_failure": [
        {
            "id": "retry_settlement",
            "label": "Retry Settlement",
            "description": "Attempt settlement again with corrected details",
            "implications": [
                "Quick resolution if successful",
                "May fail again",
                "Counterparty coordination required"
            ]
        },
        {
            "id": "escalate_to_counterparty",
            "label": "Escalate to Counterparty",
            "description": "Formally escalate issue to counterparty management",
            "implications": [
                "Higher-level attention",
                "Relationship implications",
                "Documentation required"
            ]
        },
        {
            "id": "cancel_and_rebook",
            "label": "Cancel and Rebook Trade",
            "description": "Cancel failed trade and book new one at current rates",
            "implications": [
                "Clean resolution",
                "Potential rate slippage",
                "Operational complexity"
            ]
        },
    ],
}
