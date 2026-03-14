from __future__ import annotations

import re

import httpx

from config import get_settings
from models import ImpactAssessment


def _fallback_report(assessment: ImpactAssessment) -> tuple[str, list[str]]:
    env = assessment.environmental
    eco = assessment.economic
    soc = assessment.sociological
    grid = assessment.grid_strain

    lines = [
        "## Executive Summary",
        (
            f"Composite score is {assessment.overall_score.composite_rag}. "
            f"Proposal draws {env.total_power_draw_mw:.1f} MW and implies {env.annual_carbon_tonnes:,.0f} tCO2e/year."
        ),
        (
            f"Water demand is {env.total_water_litres_per_day:,.0f} L/day "
            f"({env.pct_of_municipal_daily_supply:.2f}% of municipal supply)."
        ),
        "",
        "## Economic Reality Check",
        (
            f"Estimated permanent direct jobs: {eco.direct_permanent_jobs}, total with multiplier: "
            f"{eco.total_permanent_jobs_with_multiplier}."
        ),
        (
            f"Estimated net fiscal impact over 10 years: ${eco.net_fiscal_impact_10yr_cad:,.0f} CAD."
        ),
        "",
        "## Community Considerations",
        (
            f"Nearest First Nation: {soc.nearest_first_nation_name or 'Unknown'} at "
            f"{soc.nearest_first_nation_km:.1f} km; Indigenous consultation flag={soc.indigenous_flag}."
        ),
        f"AQHI baseline: {soc.air_quality_baseline}; vulnerability index: {soc.community_vulnerability_index:.1f}/100.",
        "",
        "## Grid Sustainability",
        (
            f"Model strain probability is {grid.strain_probability:.0%} ({grid.predicted_strain_level}), "
            f"estimated consumer rate-increase probability {grid.rate_increase_probability:.0%}."
        ),
    ]

    playbook = [
        "Require an annual verified energy and water performance report tied to permit conditions.",
        "Require a demand response participation clause if strain probability exceeds 50%.",
        "Require Indigenous consultation milestones before major construction phases.",
        "Require local workforce and apprenticeship commitments in a community benefits agreement.",
        "Require cooling technology improvements if water score is red or amber.",
    ]

    return "\n".join(lines), playbook


def _build_prompt(assessment: ImpactAssessment) -> str:
    e = assessment.environmental
    ec = assessment.economic
    s = assessment.sociological
    g = assessment.grid_strain

    return (
        "Generate a Canadian municipal planning report with strict grounding.\n"
        "Use only the numeric values provided. Do not invent or estimate numbers.\n\n"
        f"Location: {assessment.location.municipality}, {assessment.location.province}\n"
        f"IT load: {assessment.raw_inputs_used['it_load_mw']} MW; CAPEX: ${assessment.raw_inputs_used['capex_cad_millions']}M\n"
        f"Annual carbon: {e.annual_carbon_tonnes:.1f} tCO2e\n"
        f"Water/day: {e.total_water_litres_per_day:.1f} L ({e.pct_of_municipal_daily_supply:.3f}% of municipal supply)\n"
        f"Grid draw: {e.total_power_draw_mw:.1f} MW; strain probability: {g.strain_probability:.4f}\n"
        f"Direct permanent jobs: {ec.direct_permanent_jobs}\n"
        f"10-year total tax: {ec.estimated_total_tax_revenue_10yr_cad:.1f}\n"
        f"Net fiscal 10y: {ec.net_fiscal_impact_10yr_cad:.1f}\n"
        f"Indigenous flag: {s.indigenous_flag}; nearest FN km: {s.nearest_first_nation_km:.1f}\n"
        f"Community vulnerability index: {s.community_vulnerability_index:.1f}; AQHI: {s.air_quality_baseline}\n"
        f"Composite RAG: {assessment.overall_score.composite_rag}\n\n"
        "Format output sections exactly:\n"
        "1) EXECUTIVE SUMMARY\n"
        "2) ENVIRONMENTAL IMPACT\n"
        "3) ECONOMIC REALITY CHECK\n"
        "4) COMMUNITY CONSIDERATIONS\n"
        "5) GRID SUSTAINABILITY\n"
        "6) NEGOTIATION PLAYBOOK (5-7 numbered actions)"
    )


def _extract_playbook(report: str) -> list[str]:
    lines = report.splitlines()
    output: list[str] = []
    in_playbook = False
    for line in lines:
        stripped = line.strip()
        if "NEGOTIATION PLAYBOOK" in stripped.upper():
            in_playbook = True
            continue
        if in_playbook and re.match(r"^\d+[\.)]\s+", stripped):
            output.append(stripped)
        elif in_playbook and stripped.startswith("#"):
            break
    return output[:7]


async def _groq_report(assessment: ImpactAssessment) -> tuple[str, list[str]]:
    settings = get_settings()
    if not settings.groq_api_key:
        return _fallback_report(assessment)

    payload = {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "max_tokens": 1800,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a municipal planning advisor. Use only provided values. "
                    "Do not invent numeric values."
                ),
            },
            {"role": "user", "content": _build_prompt(assessment)},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds * 2) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            res.raise_for_status()
            body = res.json()
        report = body["choices"][0]["message"]["content"]
        playbook = _extract_playbook(report)
        if not playbook:
            _, fallback_playbook = _fallback_report(assessment)
            playbook = fallback_playbook
        return report, playbook
    except Exception:
        return _fallback_report(assessment)


async def generate_report(assessment: ImpactAssessment) -> tuple[str, list[str]]:
    return await _groq_report(assessment)
