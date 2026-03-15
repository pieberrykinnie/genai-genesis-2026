import asyncio
import json
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from data_sources import GeocodingUnavailableError
from llm.providers import check_bitnet_health
from orchestrator.railtracks_flow import assess_flow

settings = get_settings()
app = FastAPI(title=settings.app_name)

origins = [o.strip() for o in settings.backend_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "structured_output_note": "json_schema expected",
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
        return await assess_flow(payload)
    except GeocodingUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "geocoding_unavailable", "message": f"Unable to geocode address: {exc}"},
        ) from exc


@app.post("/api/assess/stream")
async def api_assess_stream(payload: dict):
    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def publish(event: dict) -> None:
            await queue.put(event)

        task = asyncio.create_task(assess_flow(payload, progress_callback=publish))

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
    # Placeholder: save file, extract text via backend.ingestion.pdf_extract 
    # and pass to ProposalExtractionAgent
    return {"status": "not_implemented"}
