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
}
