import os
from unittest.mock import AsyncMock, patch

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


def test_health_llm_bitnet_reachable() -> None:
    with patch("main.settings.llm_backend", "bitnet"), patch(
        "main.check_bitnet_health",
        new=AsyncMock(return_value={"reachable": True, "models": ["HF1BitLLM/Llama3-8B-1.58-100B-tokens"], "error": None}),
    ):
        r = client.get("/health/llm")

    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "bitnet"
    assert body["configured"] is True
    assert body["reachable"] is True
    assert body["models"]
    assert "structured_output_note" in body


def test_health_llm_bitnet_unreachable() -> None:
    with patch("main.settings.llm_backend", "bitnet"), patch(
        "main.check_bitnet_health",
        new=AsyncMock(return_value={"reachable": False, "models": [], "error": "connection refused"}),
    ):
        r = client.get("/health/llm")

    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "bitnet"
    assert body["reachable"] is False
    assert body["error"] == "connection refused"


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
    assert payload["sociological"]["estimated_noise_radius_m"] is not None
    assert payload["sociological"]["estimated_noise_radius_m"] >= 0
    assert "railtacks_used" in payload["methodology"]
    assert "railtacks_workflow" in payload["methodology"]
    assert "railtacks_verification_passed" in payload["methodology"]


def test_assess_stream_has_complete() -> None:
    with client.stream("POST", "/api/assess/stream", json=_sample_payload()) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"stage": "railtracks_workflow"' in body
    assert '"stage": "complete"' in body
