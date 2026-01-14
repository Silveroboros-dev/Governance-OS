"""
Wealth Pack - Option Templates.

Defines symmetric decision options for each exception type.
Options are presented equally without recommendations.
"""

WEALTH_OPTION_TEMPLATES = {
    "portfolio_drift": [
        {
            "label": "Rebalance Now",
            "description": "Execute trades to bring allocation back to target",
            "implications": [
                "Trading costs will be incurred",
                "Potential tax implications from realized gains/losses",
                "Portfolio will return to target allocation",
            ],
        },
        {
            "label": "Scheduled Rebalance",
            "description": "Schedule rebalancing for next regular rebalancing window",
            "implications": [
                "Drift may continue until scheduled date",
                "Can coordinate with other portfolio changes",
                "May benefit from more favorable market conditions",
            ],
        },
        {
            "label": "Monitor Only",
            "description": "Continue monitoring without immediate action",
            "implications": [
                "Drift may increase or decrease naturally",
                "No trading costs incurred",
                "May require escalation if drift continues",
            ],
        },
        {
            "label": "Update Target Allocation",
            "description": "Revise target allocation to align with current holdings",
            "implications": [
                "Requires client discussion and approval",
                "May change portfolio risk profile",
                "No immediate trading required",
            ],
        },
    ],
    "rebalancing_required": [
        {
            "label": "Execute Full Rebalance",
            "description": "Rebalance entire portfolio to target allocation",
            "implications": [
                "All asset classes will be adjusted",
                "Maximum trading costs and tax impact",
                "Portfolio fully aligned to targets",
            ],
        },
        {
            "label": "Partial Rebalance",
            "description": "Rebalance only the most deviated positions",
            "implications": [
                "Reduced trading costs vs full rebalance",
                "Addresses largest drift contributors",
                "Some drift may remain in other positions",
            ],
        },
        {
            "label": "Defer to Next Quarter",
            "description": "Postpone rebalancing to next scheduled window",
            "implications": [
                "Drift continues until next quarter",
                "Document reason for deferral",
                "May coordinate with expected cash flows",
            ],
        },
        {
            "label": "Tax-Aware Rebalance",
            "description": "Rebalance with tax-loss harvesting optimization",
            "implications": [
                "May take longer to execute",
                "Maximizes tax efficiency",
                "Requires wash sale rule compliance",
            ],
        },
    ],
    "suitability_mismatch": [
        {
            "label": "Adjust Portfolio Risk",
            "description": "Modify portfolio to match client risk profile",
            "implications": [
                "Trading required to adjust holdings",
                "Client suitability requirement satisfied",
                "Document change rationale",
            ],
        },
        {
            "label": "Update Client Profile",
            "description": "Review and potentially update client risk assessment",
            "implications": [
                "Requires client meeting/discussion",
                "May reveal changed circumstances",
                "Profile update requires documentation",
            ],
        },
        {
            "label": "Document Exception",
            "description": "Document mismatch with client acknowledgment",
            "implications": [
                "Client must acknowledge deviation",
                "Regulatory documentation required",
                "Periodic review commitment",
            ],
        },
        {
            "label": "Request Compliance Review",
            "description": "Escalate to compliance for formal review",
            "implications": [
                "Formal compliance process initiated",
                "Additional oversight and documentation",
                "May result in required changes",
            ],
        },
    ],
    "concentration_breach": [
        {
            "label": "Reduce Position",
            "description": "Sell portion of concentrated position",
            "implications": [
                "Reduces concentration risk",
                "May trigger capital gains tax",
                "Trading costs incurred",
            ],
        },
        {
            "label": "Hedging Strategy",
            "description": "Implement options or other hedges",
            "implications": [
                "Maintains position ownership",
                "Hedge costs ongoing",
                "Complexity in portfolio management",
            ],
        },
        {
            "label": "Client Exception",
            "description": "Document exception with client acknowledgment",
            "implications": [
                "Client retains full position",
                "Formal risk acknowledgment required",
                "Enhanced monitoring going forward",
            ],
        },
        {
            "label": "Gifting/Charitable Strategy",
            "description": "Explore gifting or charitable donation of shares",
            "implications": [
                "Tax benefits for client",
                "Reduces concentration over time",
                "Requires estate/tax planning coordination",
            ],
        },
    ],
    "tax_loss_harvest_opportunity": [
        {
            "label": "Execute Harvest",
            "description": "Sell position and purchase replacement security",
            "implications": [
                "Tax loss captured immediately",
                "Must avoid wash sale rules",
                "Replacement security selected",
            ],
        },
        {
            "label": "Partial Harvest",
            "description": "Harvest portion of position for tax efficiency",
            "implications": [
                "Partial tax benefit captured",
                "Some cost basis remains",
                "Smaller portfolio impact",
            ],
        },
        {
            "label": "Defer to Year-End",
            "description": "Wait for year-end tax planning review",
            "implications": [
                "May capture larger loss if decline continues",
                "Risk of missing opportunity if price recovers",
                "Coordinate with overall tax strategy",
            ],
        },
        {
            "label": "Decline Opportunity",
            "description": "Do not harvest - retain current position",
            "implications": [
                "No tax benefit captured",
                "Position may recover naturally",
                "No trading costs or complexity",
            ],
        },
    ],
    "client_cash_withdrawal": [
        {
            "label": "Approve and Process",
            "description": "Approve withdrawal and initiate processing",
            "implications": [
                "Cash transferred to client",
                "Liquidation executed if needed",
                "Portfolio size reduced",
            ],
        },
        {
            "label": "Approve with Liquidation Plan",
            "description": "Approve with optimized liquidation strategy",
            "implications": [
                "Tax-efficient liquidation order",
                "May take additional time",
                "Minimizes realized gains impact",
            ],
        },
        {
            "label": "Request Additional Information",
            "description": "Seek clarification on withdrawal purpose/timing",
            "implications": [
                "Delays processing",
                "May uncover planning opportunities",
                "Better client understanding",
            ],
        },
        {
            "label": "Escalate to Relationship Manager",
            "description": "Refer to senior relationship manager for review",
            "implications": [
                "Additional oversight on large withdrawal",
                "Opportunity for client retention discussion",
                "Processing delay",
            ],
        },
    ],
    "market_correlation_spike": [
        {
            "label": "Add Diversifying Assets",
            "description": "Add uncorrelated assets to portfolio",
            "implications": [
                "Reduces overall correlation",
                "May change portfolio characteristics",
                "Trading costs for new positions",
            ],
        },
        {
            "label": "Reduce Correlated Exposure",
            "description": "Reduce positions contributing to high correlation",
            "implications": [
                "Direct reduction in correlation",
                "Potential tax impact from sales",
                "Changes portfolio composition",
            ],
        },
        {
            "label": "Implement Hedging",
            "description": "Add tail risk hedges or correlation hedges",
            "implications": [
                "Provides downside protection",
                "Ongoing hedge costs",
                "Maintains current positions",
            ],
        },
        {
            "label": "Monitor and Document",
            "description": "Continue monitoring with documented rationale",
            "implications": [
                "No immediate action",
                "Correlation may normalize",
                "Document reason for inaction",
            ],
        },
    ],
    "fee_schedule_change": [
        {
            "label": "Proceed with Change",
            "description": "Implement fee change with standard notification",
            "implications": [
                "Fee change effective on scheduled date",
                "Client notification sent",
                "Standard documentation",
            ],
        },
        {
            "label": "Delay Implementation",
            "description": "Postpone fee change effective date",
            "implications": [
                "Additional time for client communication",
                "Revenue impact from delay",
                "May improve client relations",
            ],
        },
        {
            "label": "Request Exception",
            "description": "Request grandfathered rate for this client",
            "implications": [
                "Client retains current fee structure",
                "Requires management approval",
                "Creates precedent",
            ],
        },
        {
            "label": "Schedule Client Meeting",
            "description": "Discuss fee change with client before implementation",
            "implications": [
                "Proactive client communication",
                "Opportunity to explain value",
                "May prevent client concerns",
            ],
        },
    ],
}
