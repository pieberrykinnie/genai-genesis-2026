from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from calculator.economic import calc_fiscal, calc_jobs
from calculator.environmental import calc_annual_carbon, calc_grid_pressure, calc_water_use
from calculator.scoring import calc_composite_rag, score_economic, score_environmental, score_sociological
from calculator.sociological import calc_community_vulnerability_index, estimate_noise_radius_m, estimate_population_in_noise_zone
from config import get_settings
from data_sources import (
    geocode_address,
    get_aqhi_baseline,
    get_capacity_and_surplus,
    get_carbon_intensity_g_per_kwh,
    get_drought_level,
    get_indigenous_data,
    get_load_context,
    get_statcan_store,
)
from ml.grid_strain.predict import predict_grid_strain
from ml.site_fit.predict import predict_site_fit
from models import (
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


async def _fetch_public_context(proposal: ProposalInput) -> tuple[dict[str, Any], dict[str, str]]:
    province = _province_or_default(proposal)
    address = proposal.address or proposal.city or province
    geocoded_task = geocode_address(address, province)
    carbon_task = get_carbon_intensity_g_per_kwh(province)
    aqhi_task = get_aqhi_baseline(province)

    (geocoded, geocode_freshness), (carbon_intensity, carbon_freshness), (aqhi_label, aqhi_freshness) = await asyncio.gather(
        geocoded_task,
        carbon_task,
        aqhi_task,
    )

    stats_store = get_statcan_store()
    csd_id = str(geocoded.get("census_subdivision_id") or "")
    demographics, demographics_freshness = stats_store.get_csd_demographics(csd_id, province)
    total_population = int(float(demographics.get("total_population", 150000.0)))
    municipal_daily_supply_litres, water_freshness = stats_store.get_municipal_supply_l_day(csd_id, total_population)

    capacity_mw, surplus_pct, grid_freshness = get_capacity_and_surplus(province)
    load_context, load_freshness = get_load_context(province)
    drought_level, drought_freshness = get_drought_level(province)
    indigenous_context, indigenous_freshness = get_indigenous_data().nearest_reserve(
        float(geocoded.get("lat") or 0.0),
        float(geocoded.get("lng") or 0.0),
    )

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
            "area_sq_km": 250.0,
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
            f"{', '.join(policy.triggered_rules) if policy.triggered_rules else 'none'}."
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
    railtracks_meta: dict[str, Any] = {
        "railtacks_used": False,
        "railtacks_workflow": "council_decision_workflow_v1",
        "railtacks_verification_passed": False,
    }
    settings = get_settings()
    api_key = (settings.groq_api_key or "").strip()
    if not api_key or api_key.startswith("test-"):
        return _fallback_memo(proposal, environmental, economic, sociological, policy, overall_score), railtracks_meta

    try:
        import railtracks as rt

        from orchestrator.agents import MemoGroundingVerifierAgent, MemoWriterAgent
        from orchestrator.validators import validate_memo_grounding

        clause_text = {clause_id: CLAUSE_CATALOG[clause_id] for clause_id in policy.selected_clause_ids}

        def _memo_writer_prompt(
            proposal_obj: ProposalInput,
            evidence_obj: dict[str, Any],
            policy_obj: PolicyDecision,
            clause_obj: dict[str, str],
            validation_errors: list[str] | None = None,
        ) -> str:
            lines = [
                "Generate a council memo as structured output.",
                "Use only provided evidence and selected clauses.",
                f"Proposal: {proposal_obj.model_dump_json()}",
                f"Policy decision: {policy_obj.model_dump_json()}",
                f"Evidence pack: {evidence_obj}",
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
                    "Verify this memo for grounding and policy alignment.",
                    f"Proposal: {proposal_obj.model_dump_json()}",
                    f"Policy decision: {policy_obj.model_dump_json()}",
                    f"Evidence pack: {evidence_obj}",
                    f"Memo: {memo_obj.model_dump_json()}",
                    f"Clause text map: {clause_obj}",
                    "Return passed=true only if there are no issues.",
                ]
            )

        @rt.session(name="council_decision_workflow", save_state=True)
        async def _run_workflow() -> dict[str, Any]:
            rt.context.update(
                {
                    "proposal": proposal.model_dump(mode="python"),
                    "evidence_pack": evidence_pack,
                    "policy_decision": policy.model_dump(mode="python"),
                }
            )

            draft = await rt.call(
                MemoWriterAgent,
                _memo_writer_prompt(proposal, evidence_pack, policy, clause_text),
            )
            deterministic_ok, deterministic_errors = validate_memo_grounding(draft, evidence_pack, policy, proposal)
            verifier = await rt.call(
                MemoGroundingVerifierAgent,
                _memo_verifier_prompt(proposal, evidence_pack, policy, draft, clause_text),
            )

            issues = list(deterministic_errors)
            issues.extend(verifier.issues)
            if deterministic_ok and verifier.passed:
                return {
                    "memo": draft.model_dump(mode="python"),
                    "verification_passed": True,
                    "issues": [],
                }

            evidence_with_errors = {**evidence_pack, "validation_errors": issues}
            repaired = await rt.call(
                MemoWriterAgent,
                _memo_writer_prompt(
                    proposal,
                    evidence_with_errors,
                    policy,
                    clause_text,
                    validation_errors=issues,
                ),
            )
            repaired_ok, repaired_errors = validate_memo_grounding(repaired, evidence_pack, policy, proposal)
            repaired_verifier = await rt.call(
                MemoGroundingVerifierAgent,
                _memo_verifier_prompt(proposal, evidence_pack, policy, repaired, clause_text),
            )
            repaired_issues = list(repaired_errors)
            repaired_issues.extend(repaired_verifier.issues)
            return {
                "memo": repaired.model_dump(mode="python"),
                "verification_passed": bool(repaired_ok and repaired_verifier.passed),
                "issues": repaired_issues,
            }

        workflow_result, _session = await _run_workflow()
        railtracks_meta["railtacks_used"] = True
        railtracks_meta["railtacks_verification_passed"] = bool(workflow_result.get("verification_passed", False))
        return CouncilMemo(**workflow_result["memo"]), railtracks_meta
    except Exception:
        return _fallback_memo(proposal, environmental, economic, sociological, policy, overall_score), railtracks_meta


async def assess_flow(
    user_payload: dict[str, Any],
    progress_callback: ProgressCallback | None = None,
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

    await _emit(progress_callback, "railtracks_workflow", 92)
    await _emit(progress_callback, "writing_memo", 94)
    memo, railtracks_meta = await _write_memo(proposal, evidence_pack, policy, overall_score, environmental, economic, sociological)

    report_narrative = "\n\n".join(
        [
            memo.executive_summary,
            memo.environmental_section,
            memo.economic_section,
            memo.sociological_section,
            memo.recommendation_section,
        ]
    )

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
        },
    )
