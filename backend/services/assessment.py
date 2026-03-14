from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from calculator import (
    calc_annual_carbon,
    calc_composite_rag,
    calc_community_vulnerability_index,
    calc_fiscal,
    calc_grid_pressure,
    calc_jobs,
    calc_water_use,
    estimate_local_hiring_pct,
    estimate_noise_radius_m,
    estimate_population_in_noise_zone,
    score_economic,
    score_environmental,
    score_sociological,
)
from data_sources import (
    get_aqhi_baseline,
    get_capacity_and_surplus,
    get_drought_level,
    get_indigenous_data,
    get_load_context,
    get_statcan_store,
    geocode_address,
    get_carbon_intensity_g_per_kwh,
)
from llm.report_generator import generate_report
from ml.predict import predict_grid_strain
from models import (
    DataCentreProposal,
    EconomicImpact,
    EnvironmentalImpact,
    ImpactAssessment,
    LocationData,
    SociologicalImpact,
)


async def assess_proposal(proposal: DataCentreProposal) -> ImpactAssessment:
    data_freshness: dict[str, str] = {}

    geo, freshness = await geocode_address(proposal.address, proposal.province)
    data_freshness.update(freshness)
    location = LocationData(
        lat=geo["lat"],
        lng=geo["lng"],
        province=proposal.province,
        municipality=geo["municipality"],
        census_subdivision_id=geo["census_subdivision_id"] or "unknown",
        census_division_id=geo["census_division_id"] or "unknown",
    )

    carbon_intensity, freshness = await get_carbon_intensity_g_per_kwh(proposal.province)
    data_freshness.update(freshness)

    statcan_store = get_statcan_store()
    demographics, freshness = statcan_store.get_csd_demographics(location.census_subdivision_id, proposal.province)
    data_freshness.update(freshness)

    municipal_supply_l_day, freshness = statcan_store.get_municipal_supply_l_day(
        location.census_subdivision_id,
        int(demographics["total_population"]),
    )
    data_freshness.update(freshness)

    capacity_mw, surplus_pct, freshness = get_capacity_and_surplus(proposal.province)
    data_freshness.update(freshness)

    load_context, freshness = get_load_context(proposal.province)
    data_freshness.update(freshness)

    indigenous = get_indigenous_data()
    nearest, freshness = indigenous.nearest_reserve(location.lat, location.lng)
    data_freshness.update(freshness)

    drought_level, freshness = get_drought_level(proposal.province)
    data_freshness.update(freshness)

    aqhi, freshness = await get_aqhi_baseline(proposal.province)
    data_freshness.update(freshness)

    annual_carbon_tonnes, carbon_formula = calc_annual_carbon(
        proposal.it_load_mw,
        proposal.pue,
        carbon_intensity,
    )

    direct_water, indirect_water, total_water, pct_water_supply, water_formula = calc_water_use(
        proposal.it_load_mw,
        proposal.pue,
        proposal.wue,
        proposal.province,
        municipal_supply_l_day,
    )

    total_power_draw_mw, pct_of_surplus, grid_formula = calc_grid_pressure(
        proposal.it_load_mw,
        proposal.pue,
        capacity_mw,
        surplus_pct,
    )

    grid_prediction = predict_grid_strain(
        province=proposal.province,
        it_load_mw=proposal.it_load_mw,
        pue=proposal.pue,
        capacity_mw=capacity_mw,
        current_demand_mw=load_context["current_demand_mw"],
    )

    carbon_score, water_score, grid_score = score_environmental(
        annual_carbon_tonnes,
        pct_water_supply,
        grid_prediction.strain_probability,
    )

    environmental = EnvironmentalImpact(
        annual_carbon_tonnes=round(annual_carbon_tonnes, 2),
        carbon_intensity_g_per_kwh=round(carbon_intensity, 2),
        carbon_score=carbon_score,
        direct_water_litres_per_day=round(direct_water, 2),
        indirect_water_litres_per_day=round(indirect_water, 2),
        total_water_litres_per_day=round(total_water, 2),
        pct_of_municipal_daily_supply=round(pct_water_supply, 4),
        water_score=water_score,
        total_power_draw_mw=round(total_power_draw_mw, 2),
        provincial_capacity_mw=capacity_mw,
        pct_of_provincial_surplus=round(pct_of_surplus, 4),
        grid_score=grid_score,
    )

    direct_const, peak_const, direct_perm, total_perm, jobs_formula = calc_jobs(
        proposal.capex_cad,
        proposal.it_load_mw,
    )

    prop_tax, total_tax, household_increase, net_fiscal, fiscal_formula = calc_fiscal(
        province=proposal.province,
        capex_cad_millions=proposal.capex_cad,
        it_load_mw=proposal.it_load_mw,
        pue=proposal.pue,
        household_count=max(1, int(demographics["total_population"] / 2.5)),
    )

    jobs_score, fiscal_score = score_economic(direct_perm, net_fiscal)

    economic = EconomicImpact(
        direct_construction_jobs=direct_const,
        peak_construction_jobs=peak_const,
        direct_permanent_jobs=direct_perm,
        total_permanent_jobs_with_multiplier=total_perm,
        estimated_property_tax_10yr_cad=round(prop_tax, 2),
        estimated_total_tax_revenue_10yr_cad=round(total_tax, 2),
        estimated_household_electricity_increase_annual_cad=round(household_increase, 2),
        net_fiscal_impact_10yr_cad=round(net_fiscal, 2),
        jobs_score=jobs_score,
        fiscal_score=fiscal_score,
    )

    noise_radius_m = estimate_noise_radius_m(proposal.it_load_mw, proposal.cooling_type)
    pop_noise_zone = estimate_population_in_noise_zone(int(demographics["total_population"]), noise_radius_m)
    cvi = calc_community_vulnerability_index(
        unemployment_rate_pct=float(demographics["unemployment_rate"]),
        pct_low_income=float(demographics["pct_low_income_lim_at"]),
        pct_indigenous_population=float(demographics["pct_indigenous_identity"]),
        median_household_income_cad=float(demographics["median_total_income"]),
    )
    sociological_score = score_sociological(cvi)
    local_hiring = estimate_local_hiring_pct(
        postsecondary_pct=float(demographics["pct_postsecondary_certificate"]),
        facility_type=proposal.facility_type,
    )

    sociological = SociologicalImpact(
        nearest_first_nation_km=float(nearest["distance_km"]),
        nearest_first_nation_name=nearest["name"],
        treaty_territory=nearest.get("treaty"),
        active_water_advisories_nearby=int(nearest["active_water_advisories_nearby"]),
        indigenous_flag=bool(nearest["indigenous_flag"]),
        community_vulnerability_index=float(cvi),
        median_household_income_cad=float(demographics["median_total_income"]),
        unemployment_rate_pct=float(demographics["unemployment_rate"]),
        pct_indigenous_population=float(demographics["pct_indigenous_identity"]),
        pct_low_income=float(demographics["pct_low_income_lim_at"]),
        estimated_noise_radius_m=float(noise_radius_m),
        residential_population_in_noise_zone=pop_noise_zone,
        air_quality_baseline=str(aqhi),
        local_tech_workforce_pct=float(demographics["pct_postsecondary_certificate"]),
        estimated_local_hiring_pct=local_hiring,
        sociological_score=sociological_score,
    )

    overall_score = calc_composite_rag(environmental, economic, sociological, grid_prediction)

    assessment = ImpactAssessment(
        proposal_id=str(uuid.uuid4()),
        location=location,
        timestamp=datetime.now(timezone.utc),
        data_freshness=data_freshness,
        environmental=environmental,
        economic=economic,
        sociological=sociological,
        grid_strain=grid_prediction,
        overall_score=overall_score,
        negotiation_playbook=[],
        report_narrative="",
        raw_inputs_used={
            "address": proposal.address,
            "province": proposal.province,
            "it_load_mw": proposal.it_load_mw,
            "pue": proposal.pue,
            "wue": proposal.wue,
            "cooling_type": proposal.cooling_type,
            "facility_type": proposal.facility_type,
            "capex_cad_millions": proposal.capex_cad,
            "construction_months": proposal.construction_months,
            "has_onsite_generation": proposal.has_onsite_generation,
            "renewable_ppa": proposal.renewable_ppa,
            "drought_level": drought_level,
        },
        calculation_methodology=" | ".join([carbon_formula, water_formula, grid_formula, jobs_formula, fiscal_formula]),
    )

    report, playbook = await generate_report(assessment)
    assessment.report_narrative = report
    assessment.negotiation_playbook = playbook
    return assessment


async def stream_assessment_events(proposal: DataCentreProposal) -> AsyncIterator[str]:
    stages = [
        {"stage": "geocoding", "pct": 5},
        {"stage": "fetching_grid_data", "pct": 20},
        {"stage": "fetching_census_data", "pct": 35},
        {"stage": "running_calculations", "pct": 55},
        {"stage": "running_ml_model", "pct": 70},
        {"stage": "generating_report", "pct": 85},
    ]
    for stage in stages:
        yield f"data: {json.dumps(stage)}\n\n"

    result = await assess_proposal(proposal)
    payload = {
        "stage": "complete",
        "pct": 100,
        "result": result.model_dump(mode="json"),
    }
    yield f"data: {json.dumps(payload)}\n\n"
