from __future__ import annotations

from constants import PROVINCIAL_GRID_WATER_INTENSITY_L_PER_KWH


def calc_annual_carbon(it_load_mw: float, pue: float, carbon_intensity_g_per_kwh: float) -> tuple[float, str]:
    it_load_kw = it_load_mw * 1000.0
    total_energy_kwh_yr = it_load_kw * 8760.0 * pue
    carbon_kg_yr = total_energy_kwh_yr * (carbon_intensity_g_per_kwh / 1000.0)
    carbon_tonnes_yr = carbon_kg_yr / 1000.0
    formula = (
        f"IT_kW({it_load_kw:.0f}) x 8760 x PUE({pue:.2f}) x CI({carbon_intensity_g_per_kwh:.1f}) / 1,000,000"
    )
    return carbon_tonnes_yr, formula


def calc_water_use(
    it_load_mw: float,
    pue: float,
    wue: float,
    province: str,
    municipal_daily_supply_litres: float,
) -> tuple[float, float, float, float, str]:
    it_load_kw = it_load_mw * 1000.0
    direct_l_day = it_load_kw * 24.0 * pue * wue
    grid_water_intensity = PROVINCIAL_GRID_WATER_INTENSITY_L_PER_KWH.get(province, 1.5)
    indirect_l_day = it_load_kw * 24.0 * pue * grid_water_intensity
    total_l_day = direct_l_day + indirect_l_day
    pct_supply = 0.0
    if municipal_daily_supply_litres > 0:
        pct_supply = (total_l_day / municipal_daily_supply_litres) * 100.0
    formula = (
        f"direct=IT_kW x 24 x PUE x WUE, indirect=IT_kW x 24 x PUE x grid_water_intensity({grid_water_intensity})"
    )
    return direct_l_day, indirect_l_day, total_l_day, pct_supply, formula


def calc_grid_pressure(
    it_load_mw: float,
    pue: float,
    provincial_capacity_mw: float,
    provincial_surplus_pct: float,
) -> tuple[float, float, str]:
    total_power_draw_mw = it_load_mw * pue
    provincial_surplus_mw = max(0.001, provincial_capacity_mw * provincial_surplus_pct)
    pct_of_surplus = (total_power_draw_mw / provincial_surplus_mw) * 100.0
    formula = "grid_pressure=(it_load_mw x pue)/(provincial_capacity_mw x surplus_pct) x 100"
    return total_power_draw_mw, pct_of_surplus, formula
