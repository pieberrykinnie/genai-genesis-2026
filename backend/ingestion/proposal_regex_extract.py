from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _to_float(text: str) -> float | None:
    try:
        return float(text.replace(",", "").strip())
    except Exception:
        return None


def _search_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _to_float(match.group(1))


def _extract_province(text: str) -> str | None:
    province_map = {
        "ALBERTA": "AB",
        "ONTARIO": "ON",
        "QUEBEC": "QC",
        "BRITISH COLUMBIA": "BC",
        "MANITOBA": "MB",
        "SASKATCHEWAN": "SK",
        "NOVA SCOTIA": "NS",
        "NEW BRUNSWICK": "NB",
        "NEWFOUNDLAND": "NL",
        "PRINCE EDWARD ISLAND": "PE",
    }
    upper = text.upper()
    for name, code in province_map.items():
        if name in upper:
            return code
    return None


def _extract_cooling_type(text: str) -> str | None:
    checks = [
        ("liquid immersion", "liquid_immersion"),
        ("immersion", "liquid_immersion"),
        ("evaporative", "evaporative"),
        ("hybrid", "hybrid"),
        ("air-cooled", "air"),
        ("air cooled", "air"),
        ("air", "air"),
    ]
    lowered = text.lower()
    for needle, value in checks:
        if needle in lowered:
            return value
    return None


def _extract_facility_type(text: str) -> str | None:
    checks = [
        ("hyperscale", "hyperscale"),
        ("colo", "colocation"),
        ("colocation", "colocation"),
        ("enterprise", "enterprise"),
    ]
    lowered = text.lower()
    for needle, value in checks:
        if needle in lowered:
            return value
    return None


def _extract_address(text: str, province: str | None) -> str | None:
    patterns = [
        r"project\s+location[^:\n]*[:\-]\s*([^\n]{8,140})",
        r"general\s+project\s+location[^:\n]*[:\-]\s*([^\n]{8,140})",
        r"located\s+in\s+([^\n]{8,140})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
        if len(candidate) >= 8:
            return candidate

    if "indus" in text.lower():
        suffix = f", {province}" if province else ""
        return f"Indus{suffix}, Canada".replace(", ,", ",")
    return None


@dataclass
class RegexExtractionResult:
    proposal_fields: dict[str, Any]
    missing_fields: list[str]
    warnings: list[str]
    confidence: str


def extract_proposal_fields_regex(raw_text: str) -> RegexExtractionResult:
    text = re.sub(r"\s+", " ", raw_text or "").strip()
    warnings: list[str] = []

    it_load_total_mw = _search_float(r"totall?ing\s+([\d,]+)\s*MW", text)
    if it_load_total_mw is None:
        unit_mw = _search_float(r"load\s+of\s+([\d,]+)\s*MWe?", text)
        unit_count = _search_float(r"(\d+)\s*\(\d+\)\s*data halls", text) or _search_float(r"(\d+)\s*data halls", text)
        if unit_mw is not None and unit_count is not None:
            it_load_total_mw = unit_mw * unit_count
            warnings.append("Inferred total IT load from per-hall load multiplied by data hall count.")
        elif unit_mw is not None:
            it_load_total_mw = unit_mw
            warnings.append("Used per-unit load as IT load because total load was not explicit.")

    capex_cad = _search_float(r"capex[^$0-9]{0,24}\$?\s*([\d,]+(?:\.\d+)?)\s*(?:M|million)\b", text)
    if capex_cad is None:
        capex_billions = _search_float(r"capex[^$0-9]{0,24}\$?\s*([\d,]+(?:\.\d+)?)\s*(?:B|billion)\b", text)
        if capex_billions is not None:
            capex_cad = capex_billions * 1000

    pue = _search_float(r"\bPUE\b[^0-9]{0,24}([\d.]+)", text)
    wue = _search_float(r"\bWUE\b[^0-9]{0,24}([\d.]+)", text)
    construction_months = _search_float(r"construction[^0-9]{0,24}(\d{1,3})\s*months", text)

    province = _extract_province(text)
    address = _extract_address(text, province)
    cooling_type = _extract_cooling_type(text)
    facility_type = _extract_facility_type(text)
    renewable_ppa = bool(re.search(r"\bPPA\b|power purchase agreement", text, flags=re.IGNORECASE))
    has_onsite_generation = bool(re.search(r"on-site\s+(?:power|generation|data center)", text, flags=re.IGNORECASE))

    proposal_fields: dict[str, Any] = {
        "address": address,
        "province": province,
        "it_load_mw": it_load_total_mw,
        "pue": pue,
        "wue": wue,
        "cooling_type": cooling_type,
        "facility_type": facility_type,
        "capex_cad": capex_cad,
        "construction_months": int(construction_months) if construction_months is not None else None,
        "has_onsite_generation": has_onsite_generation if has_onsite_generation else None,
        "renewable_ppa": renewable_ppa if renewable_ppa else None,
    }

    required_for_assessment = [
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
    missing = [field for field in required_for_assessment if proposal_fields.get(field) is None]

    present_count = len(required_for_assessment) - len(missing)
    if present_count >= 7:
        confidence = "high"
    elif present_count >= 4:
        confidence = "moderate"
    else:
        confidence = "low"

    if missing:
        warnings.append("Some fields were not found in the PDF and should be confirmed manually.")

    return RegexExtractionResult(
        proposal_fields=proposal_fields,
        missing_fields=missing,
        warnings=warnings,
        confidence=confidence,
    )
