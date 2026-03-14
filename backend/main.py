import asyncio
import json

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
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


@app.post("/api/assess")
async def api_assess(payload: dict):
    # Runs the Railtracks flow and returns structured output
    return await assess_flow(payload)


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
