from __future__ import annotations

from constants import CARBON_THRESHOLDS, CVI_THRESHOLDS, GRID_STRAIN_THRESHOLDS, WATER_PCT_THRESHOLDS
from models import EconomicImpact, EnvironmentalImpact, GridStrainPrediction, OverallScore, SociologicalImpact


def rag_score(value: float, thresholds: tuple[float, float], invert: bool = False) -> str:
    low, high = thresholds
    if invert:
        if value >= low:
            return "green"
        if value >= high:
            return "amber"
        return "red"

    if value <= low:
        return "green"
    if value <= high:
        return "amber"
    return "red"


def score_environmental(
    annual_carbon_tonnes: float,
    water_pct: float,
    strain_probability: float,
) -> tuple[str, str, str]:
    carbon_score = rag_score(annual_carbon_tonnes, CARBON_THRESHOLDS)
    water_score = rag_score(water_pct, WATER_PCT_THRESHOLDS)
    grid_score = rag_score(strain_probability, GRID_STRAIN_THRESHOLDS)
    return carbon_score, water_score, grid_score


def score_economic(
    direct_permanent_jobs: int,
    net_fiscal_impact_10yr_cad: float,
) -> tuple[str, str]:
    jobs_score = rag_score(float(direct_permanent_jobs), (80.0, 30.0), invert=True)
    fiscal_score = rag_score(net_fiscal_impact_10yr_cad, (10_000_000.0, 0.0), invert=True)
    return jobs_score, fiscal_score


def score_sociological(cvi: float) -> str:
    return rag_score(cvi, CVI_THRESHOLDS)


def calc_composite_rag(
    environmental: EnvironmentalImpact,
    economic: EconomicImpact,
    sociological: SociologicalImpact,
    grid_strain: GridStrainPrediction,
) -> OverallScore:
    _ = grid_strain
    score_map = {"green": 1.0, "amber": 2.0, "red": 3.0}

    env_score = (
        score_map[environmental.carbon_score] * 0.33
        + score_map[environmental.water_score] * 0.33
        + score_map[environmental.grid_score] * 0.34
    )
    eco_score = score_map[economic.jobs_score] * 0.40 + score_map[economic.fiscal_score] * 0.60
    soc_score = score_map[sociological.sociological_score]

    composite_numeric = env_score * 0.40 + eco_score * 0.30 + soc_score * 0.30
    if composite_numeric < 1.7:
        rag = "green"
    elif composite_numeric < 2.3:
        rag = "amber"
    else:
        rag = "red"

    return OverallScore(
        composite_rag=rag,
        summary_sentence=(
            f"Composite risk is {rag}. Environmental pressure={environmental.grid_score}, "
            f"economic viability={economic.fiscal_score}, social sensitivity={sociological.sociological_score}."
        ),
    )
