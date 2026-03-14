from __future__ import annotations


def get_load_context(province: str) -> tuple[dict[str, float], dict[str, str]]:
    # Placeholder adapter for CER HFED integration.
    # MVP returns bounded defaults and keeps a freshness marker.
    defaults = {
        "current_demand_mw": 18000.0 if province == "ON" else 11000.0,
        "capacity_factor": 0.85 if province == "ON" else 0.78,
    }
    return defaults, {"cer_hfed": "fallback_defaults"}
