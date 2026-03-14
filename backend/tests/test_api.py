import os

from fastapi.testclient import TestClient

os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("STRICT_DATA_MODE", "false")

from main import app


client = TestClient(app)


def _sample_payload() -> dict:
    return {
        "address": "Municipal District of Greenview, Grande Prairie, Alberta",
        "province": "AB",
        "it_load_mw": 200,
        "pue": 1.5,
        "wue": 1.9,
        "cooling_type": "evaporative",
        "facility_type": "hyperscale",
        "capex_cad": 5000,
        "construction_months": 36,
        "has_onsite_generation": True,
        "renewable_ppa": False,
    }


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_assess_contract() -> None:
    r = client.post("/api/assess", json=_sample_payload())
    assert r.status_code == 200
    payload = r.json()
    assert payload["location"]["municipality"]
    assert "environmental" in payload
    assert "economic" in payload
    assert "sociological" in payload
    assert "grid_strain" in payload
    assert "overall_score" in payload
    assert "data_freshness" in payload
    assert payload["grid_strain"]["model_version"]
    assert payload["methodology"]["assessment_mode"] == "hybrid-live-and-fallback"


def test_assess_stream_has_complete() -> None:
    with client.stream("POST", "/api/assess/stream", json=_sample_payload()) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"stage": "complete"' in body
