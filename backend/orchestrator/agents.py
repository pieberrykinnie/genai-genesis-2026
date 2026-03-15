from typing import Any

import railtracks as rt
from pydantic import BaseModel

from config import get_settings
from models import CouncilMemo, PolicyDecision, ProposalInput

from .llm_factory import make_railtracks_llm

_AGENT_CACHE: dict[tuple, Any] = {}


def _agent_cache_key(prefix: str) -> tuple:
    s = get_settings()
    backend = s.llm_backend.strip().lower()
    if backend == "bitnet":
        return (prefix, backend, s.bitnet_model, s.bitnet_api_base)
    return (prefix, backend, s.groq_model, s.groq_api_base)


def clear_agent_cache() -> None:
    """Clear all cached agent instances. Call this in tests after patching LLM_BACKEND."""
    _AGENT_CACHE.clear()


def get_proposal_extraction_agent():
    key = _agent_cache_key("proposal_extraction")
    if key not in _AGENT_CACHE:
        _AGENT_CACHE[key] = rt.agent_node(
            name="ProposalExtractionAgent",
            llm=make_railtracks_llm(),
            output_schema=ProposalInput,
            system_message=(
                "Extract proposal fields into the schema. "
                "Use null for missing values. "
                "Do not infer missing numeric values. "
                "Do not perform policy analysis."
            ),
        )
    return _AGENT_CACHE[key]

class MemoInput(BaseModel):
    proposal: ProposalInput
    evidence_pack: dict
    policy_decision: PolicyDecision
    clause_text: dict[str, str]


class MemoVerificationInput(BaseModel):
    proposal: ProposalInput
    evidence_pack: dict
    policy_decision: PolicyDecision
    memo: CouncilMemo
    clause_text: dict[str, str]


class MemoVerificationResult(BaseModel):
    passed: bool
    issues: list[str] = []


def get_memo_writer_agent():
    key = _agent_cache_key("memo_writer")
    if key not in _AGENT_CACHE:
        _AGENT_CACHE[key] = rt.agent_node(
            name="MemoWriterAgent",
            llm=make_railtracks_llm(),
            system_message=(
                "You are a municipal planning memo writer. "
                "Use only the evidence pack and selected clause IDs. "
                "Do not invent numbers. "
                "Do not invent policy clauses. "
                "Explain trade-offs in plain language for council members. "
                "Return ONLY a JSON object with keys: "
                "executive_summary, environmental_section, economic_section, sociological_section, "
                "recommendation_section, clause_narratives, disclaimer."
            ),
        )
    return _AGENT_CACHE[key]


def get_memo_grounding_verifier_agent():
    key = _agent_cache_key("memo_grounding_verifier")
    if key not in _AGENT_CACHE:
        _AGENT_CACHE[key] = rt.agent_node(
            name="MemoGroundingVerifierAgent",
            llm=make_railtracks_llm(),
            system_message=(
                "You are a strict memo verifier. "
                "Validate the memo against proposal, evidence_pack, and policy_decision. "
                "Fail if memo invents numbers, conflicts with recommendation, or misaligns clause narratives. "
                "Return ONLY a JSON object with keys: passed (boolean), issues (array of strings). "
                "Return passed=true only when all checks pass. "
                "Return concise actionable issues."
            ),
        )
    return _AGENT_CACHE[key]
