from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from models import CouncilMemo, PolicyDecision, ProposalInput


NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?")


def _collect_numeric_values(value: Any) -> list[float]:
    values: list[float] = []
    if isinstance(value, bool):
        return values
    if isinstance(value, (int, float)):
        values.append(float(value))
        return values
    if isinstance(value, BaseModel):
        return _collect_numeric_values(value.model_dump(mode="python"))
    if isinstance(value, dict):
        for nested in value.values():
            values.extend(_collect_numeric_values(nested))
    elif isinstance(value, list):
        for nested in value:
            values.extend(_collect_numeric_values(nested))
    return values


def _build_allowed_numbers(evidence_pack: dict, proposal: ProposalInput | None) -> list[float]:
    base = _collect_numeric_values(evidence_pack)
    if proposal is not None:
        base.extend(_collect_numeric_values(proposal))
        if proposal.it_load_mw is not None and proposal.pue is not None:
            base.append(float(proposal.it_load_mw) * float(proposal.pue))

    # Common literal values frequently used in memo wording (e.g., 10-year framing).
    base.extend([0.0, 1.0, 10.0, 100.0])

    variants: set[float] = set()
    for n in base:
        variants.add(float(n))
        variants.add(round(float(n), 2))
        variants.add(round(float(n), 1))
        variants.add(round(float(n), 0))
        variants.add(round(float(n) * 100, 2))
        variants.add(round(float(n) / 1_000_000, 3))
    return sorted(variants)


def _extract_numeric_literals(text: str) -> list[float]:
    found: list[float] = []
    for token in NUMBER_PATTERN.findall(text):
        try:
            found.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return found


def _is_close_to_any(value: float, candidates: list[float]) -> bool:
    for c in candidates:
        if abs(value - c) <= max(5.0, abs(c) * 0.02):
            return True
    return False

def validate_memo(memo: CouncilMemo, evidence_pack: dict, policy: PolicyDecision) -> tuple[bool, list[str]]:
    errors = []
    
    if not memo.executive_summary or not memo.recommendation_section:
        errors.append("Missing required memo fields.")
        
    if policy.recommendation not in memo.recommendation_section.lower():
        errors.append(f"Recommendation section must explicitly reference '{policy.recommendation}'.")
        
    if len(memo.clause_narratives) > len(policy.selected_clause_ids):
        errors.append("Memo contains more clauses than selected by policy engine.")
        
    return len(errors) == 0, errors


def validate_memo_grounding(
    memo: CouncilMemo,
    evidence_pack: dict,
    policy: PolicyDecision,
    proposal: ProposalInput | None = None,
) -> tuple[bool, list[str]]:
    ok, errors = validate_memo(memo, evidence_pack, policy)
    all_errors = list(errors)

    if len(memo.clause_narratives) != len(policy.selected_clause_ids):
        all_errors.append("Clause narrative count must match selected policy clauses.")

    allowed_numbers = _build_allowed_numbers(evidence_pack, proposal)
    memo_text = "\n".join(
        [
            memo.executive_summary,
            memo.environmental_section,
            memo.economic_section,
            memo.sociological_section,
            memo.recommendation_section,
            "\n".join(memo.clause_narratives),
        ]
    )
    memo_numbers = _extract_numeric_literals(memo_text)

    unsupported_large_numbers: list[float] = []
    for n in memo_numbers:
        # Ignore small literals commonly used in prose; focus on meaningful quantitative claims.
        if abs(n) < 1000:
            continue
        if not _is_close_to_any(n, allowed_numbers):
            unsupported_large_numbers.append(n)

    if unsupported_large_numbers:
        sample = ", ".join(f"{n:.2f}" for n in unsupported_large_numbers[:3])
        all_errors.append(f"Memo includes unsupported numeric claims: {sample}")

    return ok and len(all_errors) == 0, all_errors
