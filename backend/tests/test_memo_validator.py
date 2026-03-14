from __future__ import annotations

from models import CouncilMemo, PolicyDecision, ProposalInput
from orchestrator.validators import validate_memo_grounding


def _policy() -> PolicyDecision:
    return PolicyDecision(
        recommendation="defer",
        triggered_rules=["low_site_fit"],
        selected_clause_ids=["DEVELOPER_FUNDED_DUE_DILIGENCE"],
        policy_summary="defer based on one rule",
    )


def _evidence_pack() -> dict:
    return {
        "environmental": {"annual_carbon_tonnes": 930312.0, "total_water_litres_per_day": 27360000.0},
        "economic": {"estimated_total_tax_revenue_10yr_cad": 1000000000.0},
        "sociological": {"residential_population_in_noise_zone": 194300},
    }


def _proposal() -> ProposalInput:
    return ProposalInput(
        address="Grande Prairie, Alberta, Canada",
        province="AB",
        it_load_mw=200,
        pue=1.5,
    )


def test_validate_memo_grounding_accepts_grounded_numbers() -> None:
    memo = CouncilMemo(
        executive_summary="Recommendation is defer.",
        environmental_section="Estimated annual carbon is 930,312 tCO2e and water is 27,360,000 L/day.",
        economic_section="Estimated tax revenue over 10 years is $1,000,000,000.",
        sociological_section="Noise zone includes about 194,300 residents.",
        recommendation_section="Council should defer.",
        clause_narratives=["Developer funds independent third-party technical review."],
        disclaimer="test",
    )
    ok, errors = validate_memo_grounding(memo, _evidence_pack(), _policy(), _proposal())
    assert ok is True
    assert errors == []


def test_validate_memo_grounding_flags_unsupported_large_number() -> None:
    memo = CouncilMemo(
        executive_summary="Recommendation is defer.",
        environmental_section="Estimated annual carbon is 930,312 tCO2e.",
        economic_section="Estimated tax revenue over 10 years is $9,999,999,999.",
        sociological_section="Noise zone includes about 194,300 residents.",
        recommendation_section="Council should defer.",
        clause_narratives=["Developer funds independent third-party technical review."],
        disclaimer="test",
    )
    ok, errors = validate_memo_grounding(memo, _evidence_pack(), _policy(), _proposal())
    assert ok is False
    assert any("unsupported numeric claims" in e for e in errors)
