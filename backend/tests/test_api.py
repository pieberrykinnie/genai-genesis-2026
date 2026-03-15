import json
import os
import time
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("STRICT_DATA_MODE", "false")

from main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


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


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_llm_bitnet_reachable(client: TestClient) -> None:
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


def test_health_llm_bitnet_unreachable(client: TestClient) -> None:
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


def test_assess_contract(client: TestClient) -> None:
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


def test_assess_stream_has_complete(client: TestClient) -> None:
    with client.stream("POST", "/api/assess/stream", json=_sample_payload()) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"stage": "railtracks_workflow"' in body
    assert '"stage": "complete"' in body


def _wait_for_job_completion(client: TestClient, job_id: str, timeout_seconds: float = 10.0) -> dict:
    deadline = time.time() + timeout_seconds
    last_status_payload: dict | None = None
    while time.time() < deadline:
        r = client.get(f"/api/memo-jobs/{job_id}")
        assert r.status_code == 200
        status_payload = r.json()
        last_status_payload = status_payload
        if status_payload["status"] in {"succeeded", "failed"}:
            return status_payload
        time.sleep(0.05)
    raise AssertionError(f"memo job did not complete before timeout: {last_status_payload}")


def test_memo_job_lifecycle(client: TestClient) -> None:
    async def fake_runner(_payload: dict) -> dict:
        return {
            "proposal_id": "proposal-test-1",
            "memo": {
                "executive_summary": "exec",
                "environmental_section": "env",
                "economic_section": "econ",
                "sociological_section": "soc",
                "recommendation_section": "rec",
                "clause_narratives": [],
                "disclaimer": "disc",
            },
            "report_narrative": "narrative",
            "methodology": {"railtacks_used": True},
        }

    with patch("main.memo_job_manager._runner", fake_runner):
        submit = client.post("/api/memo-jobs", json=_sample_payload())
        assert submit.status_code == 200
        job_id = submit.json()["job_id"]

        status_payload = _wait_for_job_completion(client, job_id)
        assert status_payload["status"] == "succeeded"

        result = client.get(f"/api/memo-jobs/{job_id}/result")
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "succeeded"
        assert body["result"]["proposal_id"] == "proposal-test-1"
        assert body["result"]["fallback_used"] is False


def test_memo_job_fallback_metadata(client: TestClient) -> None:
    async def fallback_runner(_payload: dict) -> dict:
        return {
            "proposal_id": "proposal-fallback",
            "memo": {
                "executive_summary": "exec",
                "environmental_section": "env",
                "economic_section": "econ",
                "sociological_section": "soc",
                "recommendation_section": "rec",
                "clause_narratives": [],
                "disclaimer": "disc",
            },
            "report_narrative": "narrative",
            "methodology": {"railtacks_used": False},
        }

    with patch("main.memo_job_manager._runner", fallback_runner):
        submit = client.post("/api/memo-jobs", json=_sample_payload())
        assert submit.status_code == 200
        job_id = submit.json()["job_id"]

        status_payload = _wait_for_job_completion(client, job_id)
        assert status_payload["status"] == "succeeded"

        result = client.get(f"/api/memo-jobs/{job_id}/result")
        assert result.status_code == 200
        body = result.json()
        assert body["result"]["fallback_used"] is True


def test_memo_job_not_found(client: TestClient) -> None:
    status = client.get("/api/memo-jobs/memo-job-missing")
    assert status.status_code == 404
    assert status.json()["detail"]["error"] == "memo_job_not_found"

    result = client.get("/api/memo-jobs/memo-job-missing/result")
    assert result.status_code == 404
    assert result.json()["detail"]["error"] == "memo_job_not_found"


def test_write_memo_bitnet_path(client: TestClient) -> None:
    """Exercises _write_memo → _BitNetCompatibleProvider (json_object mode) → rt.call → coerce_council_memo."""
    from config import get_settings
    from orchestrator.agents import clear_agent_cache

    settings = get_settings()

    valid_memo_json = json.dumps(
        {
            "executive_summary": "BitNet test summary for 100 MW data centre in Alberta.",
            "environmental_section": "Estimated annual carbon: 50000 tCO2e.",
            "economic_section": "CAD 2000 M CAPEX; 800 permanent jobs; 36 month construction.",
            "sociological_section": "Estimated noise radius: 250 m. Affects approx 120 residents.",
            "recommendation_section": "APPROVE",
            "clause_narratives": ["Grid capacity verified via AESO surplus margins."],
            "disclaimer": "Preliminary impact analysis. Subject to regulatory review.",
        }
    )
    valid_verifier_json = json.dumps({"passed": True, "issues": []})

    call_mock = AsyncMock(side_effect=[valid_memo_json, valid_verifier_json])

    with (
        patch.object(settings, "llm_backend", "bitnet"),
        patch.object(settings, "bitnet_api_base", "http://127.0.0.1:8080/v1"),
        patch.object(settings, "bitnet_model", "HF1BitLLM/Llama3-8B-1.58-100B-tokens"),
        patch(
            "orchestrator.railtracks_flow.check_bitnet_health",
            new=AsyncMock(
                return_value={
                    "reachable": True,
                    "models": ["HF1BitLLM/Llama3-8B-1.58-100B-tokens"],
                    "error": None,
                }
            ),
        ),
        patch("orchestrator.validators.validate_memo_grounding", return_value=(True, [])),
        patch("railtracks.call", call_mock),
    ):
        clear_agent_cache()
        r = client.post("/api/assess", json=_sample_payload())

    assert r.status_code == 200
    payload = r.json()
    assert payload["methodology"]["railtacks_used"] is True
    assert payload["methodology"]["railtacks_verification_passed"] is True
    assert payload["memo"]["executive_summary"] == "BitNet test summary for 100 MW data centre in Alberta."
    assert call_mock.call_count == 2, f"Expected 2 rt.call invocations (memo writer + verifier), got {call_mock.call_count}"
