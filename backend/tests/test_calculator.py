from calculator.environmental import calc_annual_carbon, calc_grid_pressure, calc_water_use


def test_calc_annual_carbon_positive() -> None:
    tonnes, formula = calc_annual_carbon(it_load_mw=100, pue=1.4, carbon_intensity_g_per_kwh=50)
    assert tonnes > 0
    assert "8760" in formula


def test_calc_water_use_outputs() -> None:
    direct, indirect, total, pct, _ = calc_water_use(
        it_load_mw=100,
        pue=1.4,
        wue=1.2,
        province="ON",
        municipal_daily_supply_litres=1_000_000_000,
    )
    assert direct > 0
    assert indirect > 0
    assert total == direct + indirect
    assert pct > 0


def test_calc_grid_pressure_outputs() -> None:
    draw, pct, _ = calc_grid_pressure(it_load_mw=200, pue=1.5, provincial_capacity_mw=37205, provincial_surplus_pct=0.08)
    assert draw == 300.0
    assert pct > 0
