from __future__ import annotations

from typing import Any

import railtracks as rt

from ingestion.proposal_regex_extract import extract_proposal_fields_regex
from models import ProposalInput
from orchestrator.agents import get_proposal_extraction_agent


def _missing_fields(proposal: ProposalInput) -> list[str]:
    required = [
        "address",
        "province",
        "it_load_mw",
        "pue",
        "wue",
        "cooling_type",
        "facility_type",
        "capex_cad",
        "construction_months",
    ]
    return [field for field in required if getattr(proposal, field) is None]


async def ingest_or_extract(
    payload: dict[str, Any],
    *,
    prefer_llm: bool = True,
) -> tuple[ProposalInput, dict[str, Any]]:
    """
    Normalize incoming JSON or extract proposal fields from PDF text.

    Returns a tuple of `(proposal, extraction_meta)` where `extraction_meta` is
    additive metadata used by frontend UX.
    """
    if "raw_text" not in payload:
        proposal = ProposalInput(**payload)
        return proposal, {"mode": "manual_input", "confidence": "high", "missing_fields": _missing_fields(proposal), "warnings": []}

    raw_text = str(payload.get("raw_text") or "")
    warnings: list[str] = []

    if prefer_llm:
        try:
            proposal_from_llm = await rt.call(get_proposal_extraction_agent(), {"text": raw_text})
            proposal = ProposalInput.model_validate(proposal_from_llm)
            return proposal, {
                "mode": "llm_structured",
                "confidence": "high" if len(_missing_fields(proposal)) <= 2 else "moderate",
                "missing_fields": _missing_fields(proposal),
                "warnings": warnings,
            }
        except Exception as exc:
            warnings.append(f"LLM extraction unavailable; fell back to deterministic parser ({exc.__class__.__name__}).")

    regex_result = extract_proposal_fields_regex(raw_text)
    proposal = ProposalInput(**regex_result.proposal_fields)
    warnings.extend(regex_result.warnings)
    return proposal, {
        "mode": "regex_fallback",
        "confidence": regex_result.confidence,
        "missing_fields": regex_result.missing_fields,
        "warnings": warnings,
    }
