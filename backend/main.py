from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from models import DataCentreProposal
from services.assessment import assess_proposal, stream_assessment_events

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
async def api_assess(payload: DataCentreProposal):
    return await assess_proposal(payload)


@app.post("/api/assess/stream")
async def api_assess_stream(payload: DataCentreProposal):
    return StreamingResponse(stream_assessment_events(payload), media_type="text/event-stream")
