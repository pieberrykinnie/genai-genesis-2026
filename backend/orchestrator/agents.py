import railtracks as rt
from models import ProposalInput, CouncilMemo, PolicyDecision
from pydantic import BaseModel
from .llm_factory import make_railtracks_llm

ProposalExtractionAgent = rt.agent_node(
    name="ProposalExtractionAgent",
    llm=make_railtracks_llm(),
    output_schema=ProposalInput,
    system_message=(
        "Extract proposal fields into the schema. "
        "Use null for missing values. "
        "Do not infer missing numeric values. "
        "Do not perform policy analysis."
    )
)

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


MemoWriterAgent = rt.agent_node(
    name="MemoWriterAgent",
    llm=make_railtracks_llm(),
    output_schema=CouncilMemo,
    system_message=(
        "You are a municipal planning memo writer. "
        "Use only the evidence pack and selected clause IDs. "
        "Do not invent numbers. "
        "Do not invent policy clauses. "
        "Explain trade-offs in plain language for council members."
    )
)


MemoGroundingVerifierAgent = rt.agent_node(
    name="MemoGroundingVerifierAgent",
    llm=make_railtracks_llm(),
    output_schema=MemoVerificationResult,
    system_message=(
        "You are a strict memo verifier. "
        "Validate the memo against proposal, evidence_pack, and policy_decision. "
        "Fail if memo invents numbers, conflicts with recommendation, or misaligns clause narratives. "
        "Return passed=true only when all checks pass. "
        "Return concise actionable issues."
    ),
)
