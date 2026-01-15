"""
Wealth Pack - Narrative Memo Templates.

Defines templates for wealth management-specific narrative memos.
Each template specifies structure, focus areas, and domain vocabulary.
"""

from coprocessor.schemas.narrative import MemoTemplate, MemoTemplateConfig


WEALTH_NARRATIVE_TEMPLATES = {
    MemoTemplate.WEALTH_SUITABILITY: MemoTemplateConfig(
        template_id=MemoTemplate.WEALTH_SUITABILITY,
        name="Wealth Suitability Exception Memo",
        description="Memo for client suitability mismatches and risk profile exceptions",
        pack="wealth",
        required_sections=[
            "Client Profile",
            "Suitability Issue",
            "Resolution",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Client risk profile and investment objectives",
            "Nature of suitability mismatch",
            "Holdings or recommendations in question",
            "Decision and rationale",
            "Client communication (if applicable)",
        ],
        vocabulary_hints=[
            "risk tolerance",
            "investment objective",
            "time horizon",
            "suitability assessment",
            "client profile",
            "risk capacity",
            "investment policy statement",
            "fiduciary duty",
        ],
    ),

    MemoTemplate.WEALTH_PORTFOLIO: MemoTemplateConfig(
        template_id=MemoTemplate.WEALTH_PORTFOLIO,
        name="Wealth Portfolio Exception Memo",
        description="Memo for portfolio drift, concentration, and rebalancing exceptions",
        pack="wealth",
        required_sections=[
            "Portfolio Status",
            "Exception Details",
            "Action Taken",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Current allocation vs. target",
            "Drift or concentration details",
            "Market context (if in evidence)",
            "Rebalancing decision",
            "Tax implications (if applicable)",
        ],
        vocabulary_hints=[
            "asset allocation",
            "target allocation",
            "drift threshold",
            "rebalancing",
            "concentration limit",
            "sector exposure",
            "tax-loss harvesting",
            "capital gains",
        ],
    ),

    MemoTemplate.WEALTH_CLIENT: MemoTemplateConfig(
        template_id=MemoTemplate.WEALTH_CLIENT,
        name="Wealth Client Service Memo",
        description="Memo for client-initiated requests and service exceptions",
        pack="wealth",
        required_sections=[
            "Client Request",
            "Assessment",
            "Resolution",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Nature of client request",
            "Relevant account and holdings context",
            "Compliance and suitability check",
            "Decision and execution",
            "Client communication",
        ],
        vocabulary_hints=[
            "withdrawal request",
            "transfer",
            "beneficiary",
            "distribution",
            "client instruction",
            "authorization",
            "account status",
        ],
    ),

    MemoTemplate.EXECUTIVE_SUMMARY: MemoTemplateConfig(
        template_id=MemoTemplate.EXECUTIVE_SUMMARY,
        name="Executive Summary",
        description="High-level summary for senior leadership",
        pack="wealth",
        required_sections=[
            "Key Facts",
            "Decision",
        ],
        max_sections=3,
        max_claims_per_section=4,
        length_guidelines={
            "short": {"max_sections": 2, "max_claims_per_section": 2},
            "standard": {"max_sections": 2, "max_claims_per_section": 3},
            "detailed": {"max_sections": 3, "max_claims_per_section": 4},
        },
        focus_areas=[
            "Bottom line: what happened and what was decided",
            "Key numbers only",
            "No operational details",
        ],
        vocabulary_hints=[],
    ),

    MemoTemplate.DECISION_BRIEF: MemoTemplateConfig(
        template_id=MemoTemplate.DECISION_BRIEF,
        name="Decision Brief",
        description="Standard decision documentation memo",
        pack="wealth",
        required_sections=[
            "Situation",
            "Options Considered",
            "Decision",
        ],
        max_sections=4,
        max_claims_per_section=6,
        focus_areas=[
            "What triggered the exception",
            "All options that were available",
            "Which option was selected and why",
        ],
        vocabulary_hints=[],
    ),
}


def get_wealth_template(template_id: MemoTemplate) -> MemoTemplateConfig:
    """Get a wealth narrative template by ID."""
    if template_id not in WEALTH_NARRATIVE_TEMPLATES:
        raise ValueError(f"Unknown wealth template: {template_id}")
    return WEALTH_NARRATIVE_TEMPLATES[template_id]


def get_template_for_signal_type(signal_type: str) -> MemoTemplate:
    """Map signal type to recommended template."""
    signal_to_template = {
        "portfolio_drift": MemoTemplate.WEALTH_PORTFOLIO,
        "rebalancing_required": MemoTemplate.WEALTH_PORTFOLIO,
        "concentration_breach": MemoTemplate.WEALTH_PORTFOLIO,
        "suitability_mismatch": MemoTemplate.WEALTH_SUITABILITY,
        "client_cash_withdrawal": MemoTemplate.WEALTH_CLIENT,
        "tax_loss_harvest_opportunity": MemoTemplate.WEALTH_PORTFOLIO,
        "market_correlation_spike": MemoTemplate.WEALTH_PORTFOLIO,
        "fee_schedule_change": MemoTemplate.WEALTH_CLIENT,
    }
    return signal_to_template.get(signal_type, MemoTemplate.DECISION_BRIEF)
