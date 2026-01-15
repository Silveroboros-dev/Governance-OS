"""
Treasury Pack - Narrative Memo Templates.

Defines templates for treasury-specific narrative memos.
Each template specifies structure, focus areas, and domain vocabulary.
"""

from coprocessor.schemas.narrative import MemoTemplate, MemoTemplateConfig


TREASURY_NARRATIVE_TEMPLATES = {
    MemoTemplate.TREASURY_LIQUIDITY: MemoTemplateConfig(
        template_id=MemoTemplate.TREASURY_LIQUIDITY,
        name="Treasury Liquidity Exception Memo",
        description="Memo for liquidity threshold breaches and cash management exceptions",
        pack="treasury",
        required_sections=[
            "Current Position",
            "Breach Details",
            "Decision Taken",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Current liquidity position vs. threshold",
            "Root cause of breach (if identifiable from evidence)",
            "Timeline of events",
            "Decision rationale and selected option",
            "Immediate next steps",
        ],
        vocabulary_hints=[
            "liquidity ratio",
            "cash buffer",
            "working capital",
            "credit facility",
            "cash sweep",
            "forecast variance",
            "operational cash",
            "restricted cash",
        ],
    ),

    MemoTemplate.TREASURY_POSITION: MemoTemplateConfig(
        template_id=MemoTemplate.TREASURY_POSITION,
        name="Treasury Position Limit Memo",
        description="Memo for position limit breaches and exposure exceptions",
        pack="treasury",
        required_sections=[
            "Position Summary",
            "Limit Breach",
            "Resolution",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Current position vs. authorized limit",
            "Asset class and instrument details",
            "Market context (if in evidence)",
            "Selected resolution option",
            "Risk implications",
        ],
        vocabulary_hints=[
            "position limit",
            "notional exposure",
            "mark-to-market",
            "risk-adjusted",
            "concentration limit",
            "VaR contribution",
            "hedged/unhedged",
        ],
    ),

    MemoTemplate.TREASURY_COUNTERPARTY: MemoTemplateConfig(
        template_id=MemoTemplate.TREASURY_COUNTERPARTY,
        name="Treasury Counterparty Risk Memo",
        description="Memo for counterparty credit events and relationship decisions",
        pack="treasury",
        required_sections=[
            "Counterparty Status",
            "Risk Assessment",
            "Action Taken",
        ],
        max_sections=5,
        max_claims_per_section=8,
        focus_areas=[
            "Counterparty identification and exposure",
            "Credit event details (downgrade, default indicators)",
            "Current exposure amounts",
            "Decision on relationship",
            "Exposure management actions",
        ],
        vocabulary_hints=[
            "credit rating",
            "counterparty exposure",
            "collateral",
            "netting agreement",
            "credit support annex",
            "wrong-way risk",
            "settlement risk",
        ],
    ),

    MemoTemplate.EXECUTIVE_SUMMARY: MemoTemplateConfig(
        template_id=MemoTemplate.EXECUTIVE_SUMMARY,
        name="Executive Summary",
        description="High-level summary for senior leadership",
        pack="treasury",
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
        pack="treasury",
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


def get_treasury_template(template_id: MemoTemplate) -> MemoTemplateConfig:
    """Get a treasury narrative template by ID."""
    if template_id not in TREASURY_NARRATIVE_TEMPLATES:
        raise ValueError(f"Unknown treasury template: {template_id}")
    return TREASURY_NARRATIVE_TEMPLATES[template_id]


def get_template_for_signal_type(signal_type: str) -> MemoTemplate:
    """Map signal type to recommended template."""
    signal_to_template = {
        "position_limit_breach": MemoTemplate.TREASURY_POSITION,
        "liquidity_threshold_breach": MemoTemplate.TREASURY_LIQUIDITY,
        "cash_forecast_variance": MemoTemplate.TREASURY_LIQUIDITY,
        "counterparty_credit_downgrade": MemoTemplate.TREASURY_COUNTERPARTY,
        "settlement_failure": MemoTemplate.TREASURY_COUNTERPARTY,
        "market_volatility_spike": MemoTemplate.TREASURY_POSITION,
        "fx_exposure_breach": MemoTemplate.TREASURY_POSITION,
        "covenant_breach": MemoTemplate.DECISION_BRIEF,
    }
    return signal_to_template.get(signal_type, MemoTemplate.DECISION_BRIEF)
