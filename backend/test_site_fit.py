import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import modules
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from ml.site_fit.predict import predict_site_fit

class DummyProposal:
    province = "ON"
    it_load_mw = 10.0
    pue = 1.3
    wue = 0.5
    cooling_type = "air"

async def main():
    proposal = DummyProposal()
    public_context = {
        "annual_mean_temp_c": 8.5,
        "grid_carbon_intensity": 150.0,
        "water_share_pct": 5.0,
        "drought_level": "D1",
        "aqhi_value": 4.0,
        "total_population": 500000,
        "area_sq_km": 1000.0,
        "business_count": 25000,
        "distance_to_nearest_dc_km": 12.5,
        "dc_count_within_100km": 3.0,
        "community_vulnerability_index": 45.0,
        "indigenous_flag": False,
        "municipal_daily_supply_litres": 10000000.0,
    }
    
    print("Running Site Fit prediction with dummy data...")
    res = await predict_site_fit(proposal, public_context)
    print("--- RESULT ---")
    print(res.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
