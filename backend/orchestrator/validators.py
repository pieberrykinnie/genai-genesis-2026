from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError
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
        variants.add(round(float(n) * 1_000, 2))
        variants.add(round(float(n) * 1_000_000, 2))
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


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    return str(value)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")

    candidate = cleaned[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object in LLM response.")
    return parsed


def _normalize_memo_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    text_fields = [
        "executive_summary",
        "environmental_section",
        "economic_section",
        "sociological_section",
        "recommendation_section",
        "disclaimer",
    ]
    for field in text_fields:
        value = normalized.get(field)
        if value is None:
            normalized[field] = ""
        elif not isinstance(value, str):
            normalized[field] = str(value)

    if "clause_narrative" in normalized and "clause_narratives" not in normalized:
        normalized["clause_narratives"] = normalized["clause_narrative"]

    clause_value = normalized.get("clause_narratives")
    if isinstance(clause_value, str):
        raw = clause_value.strip()
        parsed_list: list[str] | None = None
        if raw.startswith("[") and raw.endswith("]"):
            try:
                maybe = json.loads(raw.replace("'", '"'))
                if isinstance(maybe, list):
                    parsed_list = [str(item).strip() for item in maybe if str(item).strip()]
            except Exception:
                parsed_list = None
        if parsed_list is None:
            chunks = re.split(r"(?:\r?\n|;|,\s+)", raw)
            parsed_list = [c.lstrip("- ").strip() for c in chunks if c and c.strip()]
        normalized["clause_narratives"] = parsed_list
    elif isinstance(clause_value, list):
        normalized["clause_narratives"] = [str(item).strip() for item in clause_value if str(item).strip()]
    elif isinstance(clause_value, dict):
        normalized["clause_narratives"] = [str(item).strip() for item in clause_value.values() if str(item).strip()]
    elif clause_value is None:
        normalized["clause_narratives"] = []

    return normalized


def coerce_council_memo(value: Any) -> tuple[CouncilMemo | None, list[str]]:
    if isinstance(value, CouncilMemo):
        return value, []

    if isinstance(value, BaseModel):
        try:
            return CouncilMemo.model_validate(value.model_dump(mode="python")), []
        except ValidationError as exc:
            return None, [f"memo_schema_error: {exc.errors()[0]['msg']}"]

    text = _to_text(value)
    try:
        payload = _extract_json_object(text)
    except Exception as exc:
        return None, [f"memo_parse_error: {exc}"]

    try:
        return CouncilMemo.model_validate(_normalize_memo_payload(payload)), []
    except ValidationError as exc:
        msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
        return None, [f"memo_schema_error: {msg}"]


def coerce_verifier_result(value: Any) -> tuple[bool, list[str], list[str]]:
    if isinstance(value, BaseModel) and hasattr(value, "passed") and hasattr(value, "issues"):
        passed = bool(getattr(value, "passed", False))
        issues = list(getattr(value, "issues", []))
        return passed, issues, []

    text = _to_text(value)
    parse_errors: list[str] = []

    try:
        payload = _extract_json_object(text)
        passed = bool(payload.get("passed", False))
        issues_raw = payload.get("issues", [])
        issues = [str(i) for i in issues_raw] if isinstance(issues_raw, list) else [str(issues_raw)]
        return passed, issues, []
    except Exception as exc:
        parse_errors.append(f"verifier_parse_error: {exc}")

    lowered = text.lower()
    heuristic_pass = any(
        marker in lowered for marker in ['"passed": true', "passed=true", "passed: true", "no issues found"]
    )
    heuristic_issues: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            heuristic_issues.append(stripped.lstrip("- ").strip())
    if not heuristic_issues and not heuristic_pass:
        heuristic_issues.append("verifier_unparseable_response")

    return heuristic_pass, heuristic_issues, parse_errors

def validate_memo(memo: CouncilMemo, evidence_pack: dict, policy: PolicyDecision) -> tuple[bool, list[str]]:
    errors = []
    
    if not memo.executive_summary or not memo.recommendation_section:
        errors.append("Missing required memo fields.")
        
    recommendation_text = memo.recommendation_section.lower()
    expected_tokens = {
        str(policy.recommendation).lower(),
        str(policy.recommendation).replace("_", " ").lower(),
    }
    if not any(token in recommendation_text for token in expected_tokens):
        errors.append(
            f"Recommendation section must explicitly reference '{policy.recommendation}' "
            f"(or '{str(policy.recommendation).replace('_', ' ')}')."
        )
        
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
