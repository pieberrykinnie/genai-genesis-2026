from __future__ import annotations


def estimate_noise_radius_m(it_load_mw: float, cooling_type: str) -> float:
    base = 250.0 + (it_load_mw * 1.8)
    if cooling_type == "air":
        base *= 1.15
    elif cooling_type == "evaporative":
        base *= 1.05
    elif cooling_type == "liquid_immersion":
        base *= 0.8
    return round(base, 2)


def estimate_population_in_noise_zone(total_population: int, noise_radius_m: float) -> int:
    impact_ratio = min(0.35, max(0.01, (noise_radius_m / 3000.0) ** 2))
    return int(round(total_population * impact_ratio))


def calc_community_vulnerability_index(
    unemployment_rate_pct: float,
    pct_low_income: float,
    pct_indigenous_population: float,
    median_household_income_cad: float,
) -> float:
    income_component = max(0.0, min(100.0, (120_000.0 - median_household_income_cad) / 1200.0))
    unemployment_component = min(100.0, unemployment_rate_pct * 6.0)
    low_income_component = min(100.0, pct_low_income * 2.0)
    indigenous_component = min(100.0, pct_indigenous_population * 1.5)
    cvi = (
        unemployment_component * 0.30
        + low_income_component * 0.35
        + indigenous_component * 0.20
        + income_component * 0.15
    )
    return round(max(0.0, min(100.0, cvi)), 2)


def estimate_local_hiring_pct(postsecondary_pct: float, facility_type: str) -> float:
    adjust = {"hyperscale": -10.0, "enterprise": 0.0, "colocation": 5.0}
    return round(max(5.0, min(90.0, postsecondary_pct * 0.8 + adjust.get(facility_type, 0.0))), 2)
