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


def test_assess_stream_defer_memo_skips_memo_stages(client: TestClient) -> None:
    payload = {**_sample_payload(), "defer_memo": True}
    with client.stream("POST", "/api/assess/stream", json=payload) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"stage": "complete"' in body
    assert '"stage": "railtracks_workflow"' not in body
    assert '"stage": "writing_memo"' not in body
    assert '"memo": null' in body


def test_assess_defer_memo_returns_core_result(client: TestClient) -> None:
    payload = {**_sample_payload(), "defer_memo": True}
    r = client.post("/api/assess", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["memo"] is None
    assert body["report_narrative"] == ""
    assert body["methodology"]["memo_deferred"] is True


def test_extract_proposal_regex_fallback_without_llm(client: TestClient) -> None:
    pdf_text = (
        "Beacon AI Centers Indus Project. "
        "Four data halls with a power requirement of 300MW each, totalling 1200MW. "
        "Agreement with Langdon Waterworks Ltd. to receive 1,500 cubic meters per day. "
        "Project location: Indus, Alberta, Canada."
    )
    with patch("main.extract_text_from_pdf", return_value=pdf_text):
        r = client.post(
            "/api/extract-proposal",
            files={"file": ("proposal.pdf", b"%PDF-1.4 mock", "application/pdf")},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["it_load_mw"] == 1200.0
    assert body["province"] == "AB"
    assert body["address"]
    assert "_extraction" in body
    assert body["_extraction"]["mode"] == "regex_fallback"
    assert "missing_fields" in body["_extraction"]


def test_beacon_like_high_load_trends_higher_risk_than_baseline(client: TestClient) -> None:
    baseline = _sample_payload()
    beacon_like = {
        **_sample_payload(),
        "it_load_mw": 1200,
        "pue": 1.7,
        "wue": 2.2,
        "capex_cad": 9000,
        "construction_months": 48,
    }

    base_r = client.post("/api/assess", json=baseline)
    high_r = client.post("/api/assess", json=beacon_like)
    assert base_r.status_code == 200
    assert high_r.status_code == 200

    base_body = base_r.json()
    high_body = high_r.json()

    assert high_body["environmental"]["annual_carbon_tonnes"] > base_body["environmental"]["annual_carbon_tonnes"]
    assert high_body["environmental"]["total_water_litres_per_day"] > base_body["environmental"]["total_water_litres_per_day"]
    assert high_body["environmental"]["pct_of_municipal_daily_supply"] > base_body["environmental"]["pct_of_municipal_daily_supply"]

    rank = {"approve": 0, "approve_with_conditions": 1, "defer": 2, "reject": 3}
    base_rec = base_body.get("policy_decision", {}).get("recommendation", "approve")
    high_rec = high_body.get("policy_decision", {}).get("recommendation", "approve")
    assert rank[high_rec] >= rank[base_rec]


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
        patch.object(settings, "memo_verifier_mode", "conditional"),
        patch(
            "orchestrator.railtracks_flow.check_bitnet_health_cached",
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
    assert call_mock.call_count == 1, f"Expected 1 rt.call invocation (memo writer only), got {call_mock.call_count}"
