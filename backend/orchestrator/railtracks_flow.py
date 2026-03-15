from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from calculator.economic import calc_fiscal, calc_jobs
from calculator.environmental import calc_annual_carbon, calc_grid_pressure, calc_water_use
from calculator.scoring import calc_composite_rag, score_economic, score_environmental, score_sociological
from calculator.sociological import calc_community_vulnerability_index, estimate_noise_radius_m, estimate_population_in_noise_zone
from config import get_settings
from data_sources import (
    fetch_site_fit_csd_context,
    geocode_address,
    get_aqhi_baseline,
    get_capacity_and_surplus,
    get_carbon_intensity_g_per_kwh,
    get_drought_level,
    get_indigenous_data,
    get_load_context,
    get_statcan_store,
    get_annual_mean_temp,
    fetch_site_fit_datacenter_context,
)
from llm.providers import check_bitnet_health_cached
from ml.grid_strain.predict import predict_grid_strain
from ml.site_fit.predict import predict_site_fit
from models import (
    AudienceInsights,
    CouncilMemo,
    EconomicImpact,
    EnvironmentalImpact,
    GridStrainPrediction,
    ImpactAssessment,
    Location,
    OverallScore,
    PolicyDecision,
    ProposalInput,
    SiteFitPrediction,
    SociologicalImpact,
)
from policy.clause_catalog import CLAUSE_CATALOG
from policy.engine import select_policy

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]
logger = logging.getLogger(__name__)


async def _emit(progress_callback: ProgressCallback | None, stage: str, pct: int) -> None:
    if progress_callback is not None:
        await progress_callback({"stage": stage, "pct": pct})


def _province_or_default(proposal: ProposalInput) -> str:
    province = (proposal.province or "ON").upper()
    return province if province in {"ON", "AB", "BC", "QC", "MB", "SK", "NS", "NB", "NL", "PE"} else "ON"


def _location_for(proposal: ProposalInput, province: str, geocoded: dict[str, Any]) -> Location:
    address = proposal.address or "Unknown location"
    municipality = geocoded.get("municipality") or proposal.city or address.split(",")[0].strip() or address
    return Location(
        municipality=municipality,
        province=province,
        lat=float(geocoded.get("lat") or proposal.latitude or 0.0),
        lng=float(geocoded.get("lng") or proposal.longitude or 0.0),
    )


def _parse_aqhi_value(aqhi_label: str) -> float:
    try:
        return float(str(aqhi_label).split()[0])
    except Exception:
        return 3.0


def _memo_evidence_snapshot(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    environmental = evidence_pack.get("environmental", {}) if isinstance(evidence_pack, dict) else {}
    economic = evidence_pack.get("economic", {}) if isinstance(evidence_pack, dict) else {}
    sociological = evidence_pack.get("sociological", {}) if isinstance(evidence_pack, dict) else {}
    grid = evidence_pack.get("grid_strain", {}) if isinstance(evidence_pack, dict) else {}
    public_context = evidence_pack.get("public_context", {}) if isinstance(evidence_pack, dict) else {}

    return {
        "environmental": {
            "annual_carbon_tonnes": environmental.get("annual_carbon_tonnes"),
            "total_water_litres_per_day": environmental.get("total_water_litres_per_day"),
            "pct_of_municipal_daily_supply": environmental.get("pct_of_municipal_daily_supply"),
            "grid_score": environmental.get("grid_score"),
        },
        "economic": {
            "direct_permanent_jobs": economic.get("direct_permanent_jobs"),
            "net_fiscal_impact_10yr_cad": economic.get("net_fiscal_impact_10yr_cad"),
            "estimated_total_tax_revenue_10yr_cad": economic.get("estimated_total_tax_revenue_10yr_cad"),
            "jobs_gap": economic.get("jobs_gap"),
        },
        "sociological": {
            "community_vulnerability_index": sociological.get("community_vulnerability_index"),
            "indigenous_flag": sociological.get("indigenous_flag"),
            "nearest_first_nation_km": sociological.get("nearest_first_nation_km"),
            "residential_population_in_noise_zone": sociological.get("residential_population_in_noise_zone"),
        },
        "grid_strain": {
            "strain_probability": grid.get("strain_probability"),
            "rate_increase_probability": grid.get("rate_increase_probability"),
            "predicted_strain_level": grid.get("predicted_strain_level"),
            "confidence": grid.get("confidence"),
            "model_version": grid.get("model_version"),
        },
        "public_context": {
            "municipality": public_context.get("municipality"),
            "drought_level": public_context.get("drought_level"),
            "aqhi": public_context.get("aqhi"),
        },
    }


def _build_audience_insights(
    environmental: EnvironmentalImpact,
    economic: EconomicImpact,
    sociological: SociologicalImpact,
    grid_strain: GridStrainPrediction,
    policy: PolicyDecision,
) -> AudienceInsights:
    residents: list[str] = []
    if environmental.pct_of_municipal_daily_supply >= 5:
        residents.append("Local water use could become a key concern, especially in dry periods.")
    else:
        residents.append("Water-demand pressure appears manageable under current assumptions.")

    if grid_strain.strain_probability >= 0.2:
        residents.append("There is a meaningful chance of grid pressure, so power-rate questions are valid.")
    else:
        residents.append("Grid-pressure risk appears low to moderate in this scenario.")

    residents.append(
        f"Estimated people in the modeled noise influence area: {sociological.residential_population_in_noise_zone:,}."
    )

    council: list[str] = [
        f"Policy recommendation currently trends to: {policy.recommendation.replace('_', ' ')}.",
        f"Net 10-year fiscal estimate: ${economic.net_fiscal_impact_10yr_cad:,.2f}.",
    ]
    if environmental.water_score == "red":
        council.append("Use enforceable water caps, audit obligations, and clawback clauses before permit approval.")
    else:
        council.append("Use annual reporting conditions to keep utility impacts transparent post-approval.")

    return AudienceInsights(residents=residents, council=council)


def _extract_bullets(text: str) -> list[str]:
    if not text or not text.strip():
        return []

    normalized = text.replace("\\n", "\n").strip()

    # Handle cases where the model returns JSON-like arrays as text.
    if normalized.startswith("[") and normalized.endswith("]"):
        try:
            import json

            parsed = json.loads(normalized.replace("'", '"'))
            if isinstance(parsed, list):
                normalized_lines = [str(item) for item in parsed]
            else:
                normalized_lines = normalized.splitlines()
        except Exception:
            normalized_lines = normalized.splitlines()
    else:
        normalized_lines = normalized.splitlines()

    bullets: list[str] = []
    for raw in normalized_lines:
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith("for citizens") or line.lower().startswith("for councillors"):
            continue

        line = re.sub(r"^[-•*\s]+", "", line)
        line = re.sub(r"^\d+[\.)\s-]+", "", line)
        line = re.sub(r"^[\[\]\{\}\"':,\s]+", "", line)
        line = re.sub(r"[\[\]\{\}\"',;:\s]+$", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 6:
            continue
        bullets.append(line)

    # Fallback: split prose into sentence bullets.
    if not bullets:
        sentences = re.split(r"(?<=[.!?])\s+|;\s*", normalized)
        for raw in sentences:
            line = re.sub(r"^[\[\]\{\}\"':,\s-]+", "", raw.strip())
            line = re.sub(r"[\[\]\{\}\"',;:\s]+$", "", line)
            line = re.sub(r"\s+", " ", line).strip()
            if len(line) >= 12:
                bullets.append(line)

    deduped: list[str] = []
    seen: set[str] = set()
    for b in bullets:
        key = b.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(b)

    return deduped[:4]


def _audience_insights_from_memo(memo: CouncilMemo) -> AudienceInsights | None:
    section = memo.recommendation_section or ""
    if not section.strip():
        return None

    resident_match = re.search(
        r"for\s+citizens\s*:\s*(.*?)(?=for\s+councillors\s*:|$)",
        section,
        flags=re.IGNORECASE | re.DOTALL,
    )
    council_match = re.search(
        r"for\s+councillors\s*:\s*(.*)$",
        section,
        flags=re.IGNORECASE | re.DOTALL,
    )

    residents = _extract_bullets(resident_match.group(1)) if resident_match else []
    council = _extract_bullets(council_match.group(1)) if council_match else []
    if not residents and not council:
        return None
    return AudienceInsights(residents=residents, council=council)


def _audience_insights_are_rich(insights: AudienceInsights | None) -> bool:
    if insights is None:
        return False
    if len(insights.residents) < 2 or len(insights.council) < 2:
        return False
    total_words = sum(len(item.split()) for item in [*insights.residents, *insights.council])
    return total_words >= 28


async def _fetch_public_context(proposal: ProposalInput) -> tuple[dict[str, Any], dict[str, str]]:
    province = _province_or_default(proposal)
    address = proposal.address or proposal.city or province
    geocoded_task = geocode_address(address, province)
    carbon_task = get_carbon_intensity_g_per_kwh(province)
    aqhi_task = get_aqhi_baseline(province)

    (
        (geocoded, geocode_freshness),
        (carbon_intensity, carbon_freshness),
        (aqhi_label, aqhi_freshness),
    ) = await asyncio.gather(
        geocoded_task,
        carbon_task,
        aqhi_task,
    )
    
    lat = float(geocoded.get("lat") or 0.0)
    lon = float(geocoded.get("lng") or 0.0)
    
    # We await this because it uses httpx under the hood. 
    annual_mean_temp_c = await get_annual_mean_temp(lat, lon)
    # This is a synchronous calculation relying on cached pandas arrays.
    site_fit_datacenter_context = fetch_site_fit_datacenter_context(lat, lon)

    stats_store = get_statcan_store()
    csd_id = str(geocoded.get("census_subdivision_id") or "")
    
    # 🚀 NEW: Retrieve exact area and business count synced identically to training regime
    csd_features = fetch_site_fit_csd_context(csd_id)
    area_sq_km = csd_features.get("area_km2", 250.0)
    business_count = csd_features.get("business_count", 500.0)

    demographics, demographics_freshness = stats_store.get_csd_demographics(csd_id, province)
    total_population = int(float(demographics.get("total_population", csd_features.get("population", 150000.0))))
    municipal_daily_supply_litres, water_freshness = stats_store.get_municipal_supply_l_day(csd_id, total_population)

    capacity_mw, surplus_pct, grid_freshness = get_capacity_and_surplus(province)
    load_context, load_freshness = get_load_context(province)
    drought_level, drought_freshness = get_drought_level(province)
    indigenous_context, indigenous_freshness = get_indigenous_data().nearest_reserve(lat, lon)

    municipality = geocoded.get("municipality") or proposal.city or (proposal.address or "Unknown location").split(",")[0].strip()
    freshness = {
        **geocode_freshness,
        **carbon_freshness,
        **aqhi_freshness,
        **demographics_freshness,
        **water_freshness,
        **grid_freshness,
        **load_freshness,
        **drought_freshness,
        **indigenous_freshness,
    }
    return (
        {
            "province": province,
            "municipality": municipality,
            "geocoded": geocoded,
            "carbon_intensity_g_per_kwh": float(carbon_intensity),
            "aqhi_label": aqhi_label,
            "aqhi_value": _parse_aqhi_value(aqhi_label),
            "demographics": demographics,
            "total_population": total_population,
            "municipal_daily_supply_litres": float(municipal_daily_supply_litres),
            "capacity_mw": float(capacity_mw),
            "surplus_pct": float(surplus_pct),
            "load_context": load_context,
            "drought_level": drought_level,
            "indigenous_context": indigenous_context,
            "area_sq_km": area_sq_km,
            "business_count": business_count,
            "annual_mean_temp_c": annual_mean_temp_c,
            "distance_to_nearest_dc_km": site_fit_datacenter_context.get("distance_to_nearest_dc_km", 35.0),
            "dc_count_within_100km": site_fit_datacenter_context.get("dc_count_within_100km", 1.0),
        },
        freshness,
    )


def _fallback_memo(
    proposal: ProposalInput,
    environmental: EnvironmentalImpact,
    economic: EconomicImpact,
    sociological: SociologicalImpact,
    policy: PolicyDecision,
    overall_score: OverallScore,
) -> CouncilMemo:
    clause_narratives = [CLAUSE_CATALOG[clause_id] for clause_id in policy.selected_clause_ids]
    recommendation_label = policy.recommendation.replace("_", " ")
    return CouncilMemo(
        executive_summary=(
            f"Recommendation is {recommendation_label}. {overall_score.summary_sentence} "
            f"The proposal draws approximately {(proposal.it_load_mw or 0.0) * (proposal.pue or 1.0):.1f} MW including facility overhead."
        ),
        environmental_section=(
            f"Estimated annual carbon is {environmental.annual_carbon_tonnes:,.0f} tCO2e with water demand of "
            f"{environmental.total_water_litres_per_day:,.0f} L/day, equal to {environmental.pct_of_municipal_daily_supply:.2f}% of modeled municipal supply."
        ),
        economic_section=(
            f"The project supports {economic.direct_permanent_jobs} direct permanent jobs and an estimated "
            f"${economic.estimated_total_tax_revenue_10yr_cad:,.0f} in 10-year tax revenue."
        ),
        sociological_section=(
            f"Community vulnerability is {sociological.community_vulnerability_index:.1f}/100 with an estimated "
            f"{sociological.residential_population_in_noise_zone:,} residents in the noise influence area."
        ),
        recommendation_section=(
            f"Council should {recommendation_label}. Triggered policy rules: "
            f"{', '.join(policy.triggered_rules) if policy.triggered_rules else 'none'}.\n"
            "For citizens: Ask for plain-language public reporting on water, grid, jobs, and noise.\n"
            "For councillors: Tie approvals and incentives to audited performance milestones and enforceable clauses."
        ),
        clause_narratives=clause_narratives,
        disclaimer="Narrative generated from deterministic fallback calculations; validate against live source refresh before final use.",
    )


async def _write_memo(
    proposal: ProposalInput,
    evidence_pack: dict[str, Any],
    policy: PolicyDecision,
    overall_score: OverallScore,
    environmental: EnvironmentalImpact,
    economic: EconomicImpact,
    sociological: SociologicalImpact,
) -> tuple[CouncilMemo, dict[str, Any]]:
    memo_started = time.perf_counter()
    railtracks_meta: dict[str, Any] = {
        "railtacks_used": False,
        "railtacks_workflow": "council_decision_workflow_v1",
        "railtacks_verification_passed": False,
        "memo_fallback_reason": "",
        "memo_llm_calls": 0,
        "memo_elapsed_ms": 0,
    }
    settings = get_settings()
    llm_backend = settings.llm_backend.strip().lower()
    if llm_backend == "groq":
        api_key = (settings.groq_api_key or "").strip()
        llm_ready = bool(api_key) and not api_key.startswith("test-")
    elif llm_backend == "bitnet":
        bitnet_configured = bool(settings.bitnet_api_base.strip()) and bool(settings.bitnet_model.strip())
        if bitnet_configured:
            health = await check_bitnet_health_cached(settings)
            llm_ready = bool(health.get("reachable", False))
            if not llm_ready:
                railtracks_meta["memo_fallback_reason"] = str(health.get("error") or "bitnet_unreachable")
        else:
            llm_ready = False
            railtracks_meta["memo_fallback_reason"] = "bitnet_not_configured"
    else:
        llm_ready = False
        railtracks_meta["memo_fallback_reason"] = f"unsupported_llm_backend:{llm_backend}"

    if not llm_ready:
        railtracks_meta["memo_elapsed_ms"] = int((time.perf_counter() - memo_started) * 1000)
        return _fallback_memo(proposal, environmental, economic, sociological, policy, overall_score), railtracks_meta

    try:
        import railtracks as rt

        from orchestrator.agents import get_memo_grounding_verifier_agent, get_memo_writer_agent
        from orchestrator.validators import coerce_council_memo, coerce_verifier_result, validate_memo_grounding

        memo_writer_agent = get_memo_writer_agent()
        memo_grounding_verifier_agent = get_memo_grounding_verifier_agent()
        verifier_mode = settings.memo_verifier_mode.strip().lower()
        compact_evidence = _memo_evidence_snapshot(evidence_pack)

        clause_text = {clause_id: CLAUSE_CATALOG[clause_id] for clause_id in policy.selected_clause_ids}

        def _memo_writer_prompt(
            proposal_obj: ProposalInput,
            evidence_obj: dict[str, Any],
            policy_obj: PolicyDecision,
            clause_obj: dict[str, str],
            validation_errors: list[str] | None = None,
        ) -> str:
            lines = [
                "Generate a council memo as JSON.",
                "Return JSON only, no markdown and no extra commentary.",
                "Use only provided evidence and selected clauses.",
                "In recommendation_section, include the exact recommendation token from policy_decision.recommendation.",
                "In recommendation_section, use exactly this structure with line breaks:",
                "Recommendation: <exact recommendation token>",
                "For citizens:",
                "- <bullet 1>",
                "- <bullet 2>",
                "- <bullet 3>",
                "For councillors:",
                "- <bullet 1>",
                "- <bullet 2>",
                "- <bullet 3>",
                "Citizen bullets must be plain-language, concrete, and explain household/community impact (water, grid reliability/rates, noise/jobs).",
                "Councillor bullets must be policy/action oriented with measurable oversight or permit conditions.",
                "Each bullet must be 12-28 words, no quotation marks, and no JSON-like list syntax inside recommendation_section.",
                "Use numbers from evidence where useful, and avoid generic claims.",
                f"Proposal: {proposal_obj.model_dump_json()}",
                f"Policy decision: {policy_obj.model_dump_json()}",
                f"Evidence summary: {evidence_obj}",
                f"Clause text map: {clause_obj}",
            ]
            if validation_errors:
                lines.append(f"Prior validation issues to fix: {validation_errors}")
            return "\n".join(lines)

        def _memo_verifier_prompt(
            proposal_obj: ProposalInput,
            evidence_obj: dict[str, Any],
            policy_obj: PolicyDecision,
            memo_obj: CouncilMemo,
            clause_obj: dict[str, str],
        ) -> str:
            return "\n".join(
                [
                    "Verify this memo for grounding and policy alignment and return JSON.",
                    "Return JSON only with keys: passed, issues.",
                    "Allowed failure reasons only:",
                    "1) invented numeric claims not supported by proposal/evidence",
                    "2) recommendation text misaligned with policy_decision.recommendation",
                    "3) clause narratives misaligned with selected_clause_ids.",
                    "Do not fail for style, verbosity, or omitted non-critical fields.",
                    f"Proposal: {proposal_obj.model_dump_json()}",
                    f"Policy decision: {policy_obj.model_dump_json()}",
                    f"Evidence summary: {evidence_obj}",
                    f"Memo: {memo_obj.model_dump_json()}",
                    f"Clause text map: {clause_obj}",
                    "Set passed=true only if there are no issues.",
                ]
            )

        @rt.session(name="council_decision_workflow", save_state=True)
        async def _run_workflow() -> dict[str, Any]:
            rt.context.update(
                {
                    "proposal": proposal.model_dump(mode="python"),
                    "evidence_pack": compact_evidence,
                    "policy_decision": policy.model_dump(mode="python"),
                }
            )

            llm_call_count = 0
            stage_timings_ms: dict[str, int] = {}

            async def _timed_llm_call(stage: str, agent: Any, prompt: str) -> Any:
                nonlocal llm_call_count
                started = time.perf_counter()
                llm_call_count += 1
                response = await rt.call(agent, prompt)
                stage_timings_ms[stage] = int((time.perf_counter() - started) * 1000)
                return response

            draft_raw = await _timed_llm_call(
                "draft_write",
                memo_writer_agent,
                _memo_writer_prompt(proposal, compact_evidence, policy, clause_text),
            )
            draft, draft_parse_errors = coerce_council_memo(draft_raw)
            if draft is None:
                deterministic_ok = False
                deterministic_errors = list(draft_parse_errors)
                verifier_passed = False
                verifier_issues = ["verifier_skipped_due_to_memo_parse_error"]
                verifier_parse_errors: list[str] = []
            else:
                deterministic_ok, deterministic_errors = validate_memo_grounding(draft, evidence_pack, policy, proposal)
                should_verify = verifier_mode == "always" or not deterministic_ok
                if should_verify:
                    try:
                        verifier_raw = await _timed_llm_call(
                            "draft_verify",
                            memo_grounding_verifier_agent,
                            _memo_verifier_prompt(proposal, compact_evidence, policy, draft, clause_text),
                        )
                        verifier_passed, verifier_issues, verifier_parse_errors = coerce_verifier_result(verifier_raw)
                    except Exception as exc:
                        logger.warning("memo_verifier_unavailable_using_draft reason=%s", exc.__class__.__name__)
                        return {
                            "memo": draft.model_dump(mode="python"),
                            "verification_passed": bool(deterministic_ok),
                            "issues": [*deterministic_errors, f"verifier_unavailable:{exc.__class__.__name__}"],
                            "llm_call_count": llm_call_count,
                            "stage_timings_ms": stage_timings_ms,
                        }
                else:
                    verifier_passed, verifier_issues, verifier_parse_errors = True, [], []

            issues = list(deterministic_errors)
            issues.extend(verifier_issues)
            issues.extend(verifier_parse_errors)
            if draft is not None and deterministic_ok and verifier_passed:
                return {
                    "memo": draft.model_dump(mode="python"),
                    "verification_passed": True,
                    "issues": [],
                    "llm_call_count": llm_call_count,
                    "stage_timings_ms": stage_timings_ms,
                }

            evidence_with_errors = {**compact_evidence, "validation_errors": issues}
            try:
                repaired_raw = await _timed_llm_call(
                    "repair_write",
                    memo_writer_agent,
                    _memo_writer_prompt(
                        proposal,
                        evidence_with_errors,
                        policy,
                        clause_text,
                        validation_errors=issues,
                    ),
                )
            except Exception as exc:
                if draft is not None:
                    logger.warning("memo_repair_unavailable_using_draft reason=%s", exc.__class__.__name__)
                    return {
                        "memo": draft.model_dump(mode="python"),
                        "verification_passed": False,
                        "issues": [*issues, f"repair_unavailable:{exc.__class__.__name__}"],
                        "llm_call_count": llm_call_count,
                        "stage_timings_ms": stage_timings_ms,
                    }
                raise
            repaired, repaired_parse_errors = coerce_council_memo(repaired_raw)
            if repaired is None:
                return {
                    "memo": _fallback_memo(
                        proposal, environmental, economic, sociological, policy, overall_score
                    ).model_dump(mode="python"),
                    "verification_passed": False,
                    "issues": [*issues, *repaired_parse_errors],
                    "llm_call_count": llm_call_count,
                    "stage_timings_ms": stage_timings_ms,
                }

            repaired_ok, repaired_errors = validate_memo_grounding(repaired, evidence_pack, policy, proposal)
            should_verify_repair = verifier_mode == "always" or not repaired_ok
            if should_verify_repair:
                try:
                    repaired_verifier_raw = await _timed_llm_call(
                        "repair_verify",
                        memo_grounding_verifier_agent,
                        _memo_verifier_prompt(proposal, compact_evidence, policy, repaired, clause_text),
                    )
                    repaired_verifier_passed, repaired_verifier_issues, repaired_verifier_parse_errors = coerce_verifier_result(
                        repaired_verifier_raw
                    )
                except Exception as exc:
                    logger.warning("memo_repair_verifier_unavailable_using_repaired reason=%s", exc.__class__.__name__)
                    return {
                        "memo": repaired.model_dump(mode="python"),
                        "verification_passed": bool(repaired_ok),
                        "issues": [*repaired_errors, f"repair_verifier_unavailable:{exc.__class__.__name__}"],
                        "llm_call_count": llm_call_count,
                        "stage_timings_ms": stage_timings_ms,
                    }
            else:
                repaired_verifier_passed, repaired_verifier_issues, repaired_verifier_parse_errors = True, [], []
            repaired_issues = list(repaired_errors)
            repaired_issues.extend(repaired_verifier_issues)
            repaired_issues.extend(repaired_verifier_parse_errors)
            return {
                "memo": repaired.model_dump(mode="python"),
                "verification_passed": bool(repaired_ok and repaired_verifier_passed),
                "issues": repaired_issues,
                "llm_call_count": llm_call_count,
                "stage_timings_ms": stage_timings_ms,
            }

        workflow_result, _session = await _run_workflow()
        railtracks_meta["railtacks_used"] = True
        railtracks_meta["railtacks_verification_passed"] = bool(workflow_result.get("verification_passed", False))
        railtracks_meta["memo_llm_calls"] = int(workflow_result.get("llm_call_count", 0))
        railtracks_meta["memo_stage_timings_ms"] = workflow_result.get("stage_timings_ms", {})
        railtracks_meta["memo_elapsed_ms"] = int((time.perf_counter() - memo_started) * 1000)
        logger.info(
            "memo_workflow_complete backend=%s calls=%s verify_passed=%s elapsed_ms=%s stage_timings=%s",
            llm_backend,
            railtracks_meta["memo_llm_calls"],
            railtracks_meta["railtacks_verification_passed"],
            railtracks_meta["memo_elapsed_ms"],
            railtracks_meta.get("memo_stage_timings_ms", {}),
        )
        return CouncilMemo(**workflow_result["memo"]), railtracks_meta
    except Exception as exc:
        detail = str(exc)
        if "rate_limit_exceeded" in detail.lower() or "rate limit" in detail.lower():
            railtracks_meta["memo_fallback_reason"] = "workflow_exception:rate_limit_exceeded"
        elif detail:
            # Keep reason compact but specific enough for demo diagnostics.
            compact = detail.replace("\n", " ").strip()[:140]
            railtracks_meta["memo_fallback_reason"] = f"workflow_exception:{exc.__class__.__name__}:{compact}"
        else:
            railtracks_meta["memo_fallback_reason"] = f"workflow_exception:{exc.__class__.__name__}"
        railtracks_meta["memo_elapsed_ms"] = int((time.perf_counter() - memo_started) * 1000)
        logger.exception("memo_workflow_failed reason=%s", railtracks_meta["memo_fallback_reason"])
        return _fallback_memo(proposal, environmental, economic, sociological, policy, overall_score), railtracks_meta


async def assess_flow(
    user_payload: dict[str, Any],
    progress_callback: ProgressCallback | None = None,
    include_memo: bool = True,
) -> ImpactAssessment:
    await _emit(progress_callback, "proposal_ingest", 10)
    proposal = ProposalInput(**user_payload)

    province = _province_or_default(proposal)
    it_load_mw = float(proposal.it_load_mw or 0.0)
    pue = float(proposal.pue or 1.35)
    wue = float(proposal.wue or 0.0)
    capex_cad_millions = float(proposal.capex_cad or 0.0)

    await _emit(progress_callback, "fetching_public_data", 30)
    public_context, freshness = await _fetch_public_context(proposal)
    location = _location_for(proposal, province, public_context["geocoded"])
    carbon_intensity = float(public_context["carbon_intensity_g_per_kwh"])
    municipal_daily_supply_litres = float(public_context["municipal_daily_supply_litres"])
    total_population = int(public_context["total_population"])
    household_count = max(1, int(round(total_population / 2.45)))
    demographics = public_context["demographics"]
    current_demand_mw = float(public_context["load_context"].get("current_demand_mw", 0.0))
    capacity_mw = float(public_context["capacity_mw"])
    surplus_pct = float(public_context["surplus_pct"])

    await _emit(progress_callback, "running_calculations", 55)
    annual_carbon_tonnes, carbon_formula = calc_annual_carbon(it_load_mw, pue, carbon_intensity)
    _, _, total_water_litres_per_day, pct_of_municipal_daily_supply, water_formula = calc_water_use(
        it_load_mw,
        pue,
        wue,
        province,
        municipal_daily_supply_litres,
    )
    total_power_draw_mw, pct_of_surplus, grid_formula = calc_grid_pressure(
        it_load_mw,
        pue,
        capacity_mw,
        surplus_pct,
    )

    await _emit(progress_callback, "running_grid_model", 70)
    grid_strain = await predict_grid_strain(
        province=province,
        it_load_mw=it_load_mw,
        pue=pue,
        capacity_mw=int(round(capacity_mw)),
        current_utilization=(current_demand_mw / capacity_mw) if capacity_mw > 0 else None,
    )
    carbon_score, water_score, grid_score = score_environmental(
        annual_carbon_tonnes,
        pct_of_municipal_daily_supply,
        grid_strain.strain_probability,
    )

    direct_construction_jobs, peak_construction_jobs, direct_permanent_jobs, total_permanent_jobs, jobs_formula = calc_jobs(
        capex_cad_millions,
        it_load_mw,
    )
    _, estimated_total_tax_revenue_10yr_cad, _, net_fiscal_impact_10yr_cad, fiscal_formula = calc_fiscal(
        province,
        capex_cad_millions,
        it_load_mw,
        pue,
        household_count,
    )
    jobs_score, fiscal_score = score_economic(direct_permanent_jobs, net_fiscal_impact_10yr_cad)

    noise_radius_m = estimate_noise_radius_m(it_load_mw, proposal.cooling_type or "air")
    residential_population_in_noise_zone = estimate_population_in_noise_zone(total_population, noise_radius_m)
    community_vulnerability_index = calc_community_vulnerability_index(
        float(demographics.get("unemployment_rate", 6.1)),
        float(demographics.get("pct_low_income_lim_at", 13.0)),
        float(demographics.get("pct_indigenous_identity", 4.5)),
        float(demographics.get("median_total_income", 76000.0)),
    )
    sociological_score = score_sociological(community_vulnerability_index)
    indigenous_context = public_context["indigenous_context"]
    nearest_first_nation_km = float(indigenous_context.get("distance_km", 120.0))
    indigenous_flag = bool(indigenous_context.get("indigenous_flag", False))

    environmental = EnvironmentalImpact(
        annual_carbon_tonnes=round(annual_carbon_tonnes, 2),
        carbon_score=carbon_score,
        total_water_litres_per_day=round(total_water_litres_per_day, 2),
        water_score=water_score,
        grid_score=grid_score,
        pct_of_municipal_daily_supply=round(pct_of_municipal_daily_supply, 4),
    )
    economic = EconomicImpact(
        direct_permanent_jobs=direct_permanent_jobs,
        total_permanent_jobs_with_multiplier=total_permanent_jobs,
        estimated_total_tax_revenue_10yr_cad=round(estimated_total_tax_revenue_10yr_cad, 2),
        net_fiscal_impact_10yr_cad=round(net_fiscal_impact_10yr_cad, 2),
        fiscal_score=fiscal_score,
        jobs_score=jobs_score,
    )
    sociological = SociologicalImpact(
        indigenous_flag=indigenous_flag,
        community_vulnerability_index=community_vulnerability_index,
        sociological_score=sociological_score,
        nearest_first_nation_km=nearest_first_nation_km,
        air_quality_baseline=str(public_context["aqhi_label"]),
        residential_population_in_noise_zone=residential_population_in_noise_zone,
        estimated_noise_radius_m=round(noise_radius_m, 2),
    )

    await _emit(progress_callback, "running_site_fit_model", 80)
    site_fit_context = {
        **public_context,
        "community_vulnerability_index": sociological.community_vulnerability_index,
        "indigenous_flag": sociological.indigenous_flag,
    }
    site_fit = await predict_site_fit(proposal, site_fit_context)

    overall_score = calc_composite_rag(environmental, economic, sociological, grid_strain)
    jobs_gap = max(0, int((proposal.jobs_promised or direct_permanent_jobs) - total_permanent_jobs))
    evidence_pack = {
        "environmental": {**environmental.model_dump(), "carbon_formula": carbon_formula, "water_formula": water_formula, "grid_formula": grid_formula},
        "economic": {
            **economic.model_dump(),
            "direct_construction_jobs": direct_construction_jobs,
            "peak_construction_jobs": peak_construction_jobs,
            "jobs_gap": jobs_gap,
            "jobs_formula": jobs_formula,
            "fiscal_formula": fiscal_formula,
        },
        "sociological": {
            **sociological.model_dump(),
            "noise_radius_m": noise_radius_m,
            "nearest_first_nation_name": indigenous_context.get("name"),
            "treaty": indigenous_context.get("treaty"),
            "active_water_advisories_nearby": indigenous_context.get("active_water_advisories_nearby"),
        },
        "grid_strain": grid_strain.model_dump(),
        "site_fit": site_fit.model_dump(),
        "public_context": {
            "current_demand_mw": current_demand_mw,
            "drought_level": public_context["drought_level"],
            "aqhi": public_context["aqhi_label"],
            "municipality": public_context["municipality"],
        },
    }

    await _emit(progress_callback, "selecting_policy", 88)
    policy = select_policy(evidence_pack)
    audience_insights_fallback = _build_audience_insights(environmental, economic, sociological, grid_strain, policy)

    if include_memo:
        await _emit(progress_callback, "railtracks_workflow", 92)
        await _emit(progress_callback, "writing_memo", 94)
        memo, railtracks_meta = await _write_memo(
            proposal, evidence_pack, policy, overall_score, environmental, economic, sociological
        )
        report_narrative = "\n\n".join(
            [
                memo.executive_summary,
                memo.environmental_section,
                memo.economic_section,
                memo.sociological_section,
                memo.recommendation_section,
            ]
        )
    else:
        memo = None
        report_narrative = ""
        railtracks_meta = {
            "railtacks_used": False,
            "railtacks_workflow": "council_decision_workflow_v1",
            "railtacks_verification_passed": False,
            "memo_fallback_reason": "memo_deferred",
            "memo_llm_calls": 0,
            "memo_elapsed_ms": 0,
            "memo_stage_timings_ms": {},
        }

    memo_audience = _audience_insights_from_memo(memo) if memo is not None else None
    use_memo_audience = bool(
        railtracks_meta.get("railtacks_used", False)
        and _audience_insights_are_rich(memo_audience)
    )
    audience_insights = memo_audience if use_memo_audience and memo_audience is not None else audience_insights_fallback

    return ImpactAssessment(
        proposal_id=f"proposal-{uuid4().hex[:12]}",
        timestamp=datetime.now(UTC),
        location=location,
        data_freshness=freshness,
        proposal=proposal,
        environmental=environmental,
        economic=economic,
        sociological=sociological,
        grid_strain=grid_strain,
        site_fit=site_fit,
        overall_score=overall_score,
        audience_insights=audience_insights,
        policy_decision=policy,
        memo=memo,
        negotiation_playbook=[CLAUSE_CATALOG[clause_id] for clause_id in policy.selected_clause_ids],
        report_narrative=report_narrative,
        evidence_pack=evidence_pack,
        methodology={
            "assessment_mode": "hybrid-live-and-fallback",
            "grid_model": grid_strain.model_version,
            "site_fit_model": site_fit.model_version,
            "carbon_source": freshness.get("grid_carbon_source", freshness.get("electricity_maps", "unknown")),
            "municipal_water_source": freshness.get("statcan_water", "fallback_population_estimate"),
            "railtacks_used": railtracks_meta["railtacks_used"],
            "railtacks_workflow": railtracks_meta["railtacks_workflow"],
            "railtacks_verification_passed": railtracks_meta["railtacks_verification_passed"],
            "memo_fallback_reason": railtracks_meta.get("memo_fallback_reason", ""),
            "memo_llm_calls": railtracks_meta.get("memo_llm_calls", 0),
            "memo_elapsed_ms": railtracks_meta.get("memo_elapsed_ms", 0),
            "memo_stage_timings_ms": railtracks_meta.get("memo_stage_timings_ms", {}),
            "memo_deferred": not include_memo,
        },
    )
