import asyncio
import json
import os
import tempfile
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from data_sources import GeocodingUnavailableError
from ingestion.pdf_extract import extract_text_from_pdf
from ingestion.proposal_normalize import ingest_or_extract
from llm.providers import check_bitnet_health
from orchestrator.memo_jobs import MemoJobManager, QueueFullError
from orchestrator.railtracks_flow import assess_flow

settings = get_settings()
app = FastAPI(title=settings.app_name)
memo_job_manager = MemoJobManager(
    queue_maxsize=settings.memo_job_queue_maxsize,
    worker_count=settings.memo_job_worker_count,
    timeout_seconds=settings.memo_job_timeout_seconds,
)

origins = [o.strip() for o in settings.backend_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    await memo_job_manager.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await memo_job_manager.stop()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/llm")
async def health_llm() -> dict[str, Any]:
    backend = settings.llm_backend.strip().lower()

    if backend == "bitnet":
        configured = bool(settings.bitnet_api_base.strip()) and bool(settings.bitnet_model.strip())
        if not configured:
            return {
                "backend": "bitnet",
                "configured": False,
                "reachable": False,
                "models": [],
                "structured_output_note": "json_object only (not json_schema)",
                "error": "bitnet_backend_not_configured",
            }

        health_result = await check_bitnet_health(settings)
        return {
            "backend": "bitnet",
            "configured": True,
            "reachable": bool(health_result.get("reachable", False)),
            "models": list(health_result.get("models", [])),
            "structured_output_note": "json_object only (not json_schema)",
            "error": health_result.get("error"),
        }

    if backend == "groq":
        api_key = (settings.groq_api_key or "").strip()
        return {
            "backend": "groq",
            "configured": bool(api_key),
            "reachable": None,
            "models": [settings.groq_model] if settings.groq_model.strip() else [],
            "structured_output_note": "json_schema preferred; auto-fallback to json_object if unsupported by model",
            "error": None,
        }

    return {
        "backend": backend or "unknown",
        "configured": False,
        "reachable": False,
        "models": [],
        "structured_output_note": "unknown",
        "error": "unsupported_llm_backend",
    }


@app.post("/api/assess")
async def api_assess(payload: dict):
    # Runs the Railtracks flow and returns structured output
    try:
        use_payload = dict(payload)
        include_memo = not bool(use_payload.pop("defer_memo", False))
        return await assess_flow(use_payload, include_memo=include_memo)
    except GeocodingUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "geocoding_unavailable", "message": f"Unable to geocode address: {exc}"},
        ) from exc


@app.post("/api/memo-jobs")
async def api_submit_memo_job(payload: dict) -> dict[str, Any]:
    try:
        job_id = await memo_job_manager.submit(payload)
    except QueueFullError as exc:
        raise HTTPException(
            status_code=429,
            detail={"error": "memo_job_queue_full", "message": "Memo job queue is full, try again shortly."},
        ) from exc

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/memo-jobs/{job_id}")
async def api_get_memo_job_status(job_id: str) -> dict[str, Any]:
    status = await memo_job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail={"error": "memo_job_not_found", "job_id": job_id})
    return status


@app.get("/api/memo-jobs/{job_id}/result")
async def api_get_memo_job_result(job_id: str) -> dict[str, Any]:
    job = await memo_job_manager.get_result(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"error": "memo_job_not_found", "job_id": job_id})

    status = str(job.get("status") or "")
    if status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail={"error": "memo_job_not_complete", "job_id": job_id, "status": status})
    if status == "failed":
        raise HTTPException(
            status_code=422,
            detail={"error": "memo_job_failed", "job_id": job_id, "message": job.get("error") or "unknown_error"},
        )

    return {"job_id": job_id, "status": status, "result": job.get("result")}


@app.post("/api/assess/stream")
async def api_assess_stream(payload: dict):
    use_payload = dict(payload)
    include_memo = not bool(use_payload.pop("defer_memo", False))

    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def publish(event: dict) -> None:
            await queue.put(event)

        task = asyncio.create_task(assess_flow(use_payload, progress_callback=publish, include_memo=include_memo))

        try:
            while True:
                if task.done() and queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                yield f"data: {json.dumps(event)}\n\n"

            result = await task
            yield f"data: {json.dumps({'stage': 'complete', 'pct': 100, 'result': result.model_dump(mode='json')})}\n\n"
        except Exception as exc:
            if not task.done():
                task.cancel()
            yield f"data: {json.dumps({'stage': 'error', 'pct': 100, 'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/extract-proposal")
async def api_extract_proposal(file: UploadFile = File(...)):
    raw_bytes = await file.read()

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name
        text = extract_text_from_pdf(tmp_path)
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    # Check whether LLM extraction is available; fallback parser still runs if unavailable.
    current_settings = get_settings()
    llm_backend = current_settings.llm_backend.strip().lower()
    if llm_backend == "groq":
        api_key = (current_settings.groq_api_key or "").strip()
        llm_ready = bool(api_key) and not api_key.startswith("test-")
    elif llm_backend == "bitnet":
        bitnet_configured = (
            bool(current_settings.bitnet_api_base.strip())
            and bool(current_settings.bitnet_model.strip())
        )
        if bitnet_configured:
            health = await check_bitnet_health(current_settings)
            llm_ready = bool(health.get("reachable", False))
        else:
            llm_ready = False
    else:
        llm_ready = False

    proposal, extraction_meta = await ingest_or_extract({"raw_text": text}, prefer_llm=llm_ready)
    return {**proposal.model_dump(mode="json"), "_extraction": extraction_meta}


@app.post("/api/impact-summary")
async def api_impact_summary(payload: dict) -> dict:
    """Generate AI-authored resident and council impact bullet points for a completed assessment.

    Accepts a full ImpactAssessment JSON payload and returns
    ``{ resident_bullets: [...], council_bullets: [...] }``.
    Falls back to deterministic bullets if the LLM is unavailable.
    """
    from models import ImpactAssessment as ImpactAssessmentModel
    from orchestrator.railtracks_flow import generate_impact_summary

    try:
        assessment = ImpactAssessmentModel(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_assessment_payload", "message": str(exc)}) from exc

    summary = await generate_impact_summary(assessment)
    return summary.model_dump(mode="json")
