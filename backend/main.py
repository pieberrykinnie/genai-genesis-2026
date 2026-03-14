from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from backend.orchestrator.railtracks_flow import assess_flow

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
    # Placeholder: hook into Railtracks session broadcast
    async def event_generator():
        yield 'data: {"stage": "started"}\n\n'
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/extract-proposal")
async def api_extract_proposal(file: UploadFile = File(...)):
    # Placeholder: save file, extract text via backend.ingestion.pdf_extract 
    # and pass to ProposalExtractionAgent
    return {"status": "not_implemented"}
