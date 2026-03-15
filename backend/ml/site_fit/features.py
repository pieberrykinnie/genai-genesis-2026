from __future__ import annotations

from constants import DROUGHT_SCORE, PROVINCIAL_GRID_WATER_INTENSITY_L_PER_KWH


def extract_site_features(proposal, public_context):
    province = (proposal.province or public_context.get("province") or "ON").upper()
    it_load_mw = float(getattr(proposal, "it_load_mw", 0.0) or 0.0)
    pue = float(getattr(proposal, "pue", 1.35) or 1.35)
    wue = float(getattr(proposal, "wue", 0.0) or 0.0)

    municipal_supply_litres = float(public_context.get("municipal_daily_supply_litres") or 0.0)
    grid_water_intensity = PROVINCIAL_GRID_WATER_INTENSITY_L_PER_KWH.get(province, 1.4)
    total_water_litres_per_day = it_load_mw * 1000.0 * 24.0 * pue * (wue + grid_water_intensity)
    water_share_pct = (total_water_litres_per_day / municipal_supply_litres) * 100.0 if municipal_supply_litres > 0 else 0.0

    drought_level = str(public_context.get("drought_level") or "D0")
    drought_score = float(DROUGHT_SCORE.get(drought_level, 1))
    aqhi_value = float(public_context.get("aqhi_value") or 3.0)
    carbon_intensity = float(public_context.get("carbon_intensity_g_per_kwh") or 250.0)
    population = float(public_context.get("total_population") or 150000.0)
    area_sq_km = float(public_context.get("area_sq_km") or 250.0)
    population_density = population / max(area_sq_km, 1.0)
    
    business_count = float(public_context.get("business_count") or 500.0)
    business_density = business_count / max(area_sq_km, 1.0)
    
    annual_mean_temp_c = float(public_context.get("annual_mean_temp_c") or 5.0)

    nearest_dc_km = float(public_context.get("distance_to_nearest_dc_km") or (35.0 if province in {"ON", "AB", "BC", "QC"} else 80.0))
    dc_count_within_100km = float(public_context.get("dc_count_within_100km") or (4.0 if province in {"ON", "AB"} else 1.0))
    community_vulnerability_index = float(public_context.get("community_vulnerability_index") or 35.0)
    indigenous_flag = float(bool(public_context.get("indigenous_flag")))

    water_stress_score = min(100.0, water_share_pct * 3.2 + drought_score * 12.0)
    cooling_penalty = 0.0 if (proposal.cooling_type or "air") in {"liquid_immersion", "hybrid"} else 7.5

    return {
        "province": province,
        "grid_carbon_intensity": carbon_intensity,
        "water_share_pct": round(water_share_pct, 4),
        "water_stress_score": round(water_stress_score, 4),
        "drought_score": drought_score,
        "aqhi_value": aqhi_value,
        "annual_mean_temp_c": round(annual_mean_temp_c, 2),
        "population_density": round(population_density, 4),
        "business_density": round(business_density, 4),
        "distance_to_nearest_dc_km": nearest_dc_km,
        "dc_count_within_100km": dc_count_within_100km,
        "community_vulnerability_index": community_vulnerability_index,
        "indigenous_flag": indigenous_flag,
        "cooling_penalty": cooling_penalty,
    }
