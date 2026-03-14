import railtracks as rt
from models import ProposalInput
from backend.orchestrator.agents import ProposalExtractionAgent

async def ingest_or_extract(payload: dict) -> ProposalInput:
    '''
    Normalize incoming JSON or run the ProposalExtractionAgent over PDF raw text.
    '''
    if "raw_text" in payload:
        # Run agent
        proposal = await rt.call(ProposalExtractionAgent, {"text": payload["raw_text"]})
        return proposal
    else:
        return ProposalInput(**payload)
