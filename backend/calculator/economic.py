from __future__ import annotations

from constants import AUX_ELECTRICITY_RATE_PER_KWH_CAD


def calc_jobs(capex_cad_millions: float, it_load_mw: float) -> tuple[int, int, int, int, str]:
    direct_construction = int(round(capex_cad_millions * 12.0))
    peak_construction = int(round(direct_construction * 1.8))
    jobs_per_mw = 0.5
    direct_permanent = max(20, min(400, int(round(it_load_mw * jobs_per_mw))))
    total_permanent = int(round(direct_permanent * 2.1))
    formula = "construction_jobs=capex_millions x 12; permanent_jobs=it_load_mw x 0.5"
    return direct_construction, peak_construction, direct_permanent, total_permanent, formula


def calc_fiscal(
    province: str,
    capex_cad_millions: float,
    it_load_mw: float,
    pue: float,
    household_count: int,
) -> tuple[float, float, float, float, str]:
    capex_cad = capex_cad_millions * 1_000_000.0
    property_tax_10yr = capex_cad * 0.12
    total_tax_10yr = capex_cad * 0.20

    annual_energy_kwh = it_load_mw * 1000.0 * 8760.0 * pue
    demand_increase_factor = min(0.25, it_load_mw / 8000.0)
    province_rate = AUX_ELECTRICITY_RATE_PER_KWH_CAD.get(province, 0.16)
    household_annual_increase = province_rate * demand_increase_factor * 9000.0 * 0.30

    infra_cost_10yr = capex_cad * 0.08 + annual_energy_kwh * 0.002
    net_fiscal = total_tax_10yr - infra_cost_10yr - household_annual_increase * max(household_count, 1)
    formula = "tax=capex x 0.20, net=tax-infrastructure-household_rate_pressure"
    return property_tax_10yr, total_tax_10yr, household_annual_increase, net_fiscal, formula
