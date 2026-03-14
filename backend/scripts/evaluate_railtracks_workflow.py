from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import railtracks as rt
from railtracks.evaluations import JudgeEvaluator, ToolUseEvaluator, evaluate, extract_agent_data_points
from railtracks.evaluations.evaluators.metrics import LLMMetric

from models import PolicyDecision, ProposalInput
from orchestrator.agents import MemoGroundingVerifierAgent, MemoWriterAgent
from orchestrator.llm_factory import make_railtracks_llm
from orchestrator.validators import validate_memo_grounding
from policy.clause_catalog import CLAUSE_CATALOG


def _scenario_payloads() -> list[dict]:
    return [
        {
            "name": "ab_high_load",
            "proposal": ProposalInput(
                address="Municipal District of Greenview, Grande Prairie, Alberta, Canada",
                province="AB",
                it_load_mw=200.0,
                pue=1.5,
                wue=1.9,
                cooling_type="evaporative",
                facility_type="hyperscale",
                capex_cad=5000.0,
                construction_months=36,
                has_onsite_generation=True,
                renewable_ppa=False,
            ),
            "policy": PolicyDecision(
                recommendation="defer",
                triggered_rules=["low_site_fit", "noise_exposure"],
                selected_clause_ids=["DEVELOPER_FUNDED_DUE_DILIGENCE", "NOISE_ABATEMENT"],
                policy_summary="defer based on two triggered rules",
            ),
            "evidence_pack": {
                "environmental": {
                    "annual_carbon_tonnes": 930312.0,
                    "total_water_litres_per_day": 27360000.0,
                    "pct_of_municipal_daily_supply": 2.92,
                },
                "economic": {"estimated_total_tax_revenue_10yr_cad": 1000000000.0},
                "sociological": {"residential_population_in_noise_zone": 194300},
                "grid_strain": {"strain_probability": 0.0176},
            },
        },
        {
            "name": "qc_lower_risk",
            "proposal": ProposalInput(
                address="Levis, Quebec, Canada",
                province="QC",
                it_load_mw=100.0,
                pue=1.3,
                wue=0.8,
                cooling_type="liquid_immersion",
                facility_type="enterprise",
                capex_cad=800.0,
                construction_months=24,
                has_onsite_generation=False,
                renewable_ppa=True,
            ),
            "policy": PolicyDecision(
                recommendation="approve_with_conditions",
                triggered_rules=["annual_reporting"],
                selected_clause_ids=["ANNUAL_TRANSPARENCY_REPORT"],
                policy_summary="approve with annual reporting condition",
            ),
            "evidence_pack": {
                "environmental": {
                    "annual_carbon_tonnes": 21000.0,
                    "total_water_litres_per_day": 8100000.0,
                    "pct_of_municipal_daily_supply": 0.8,
                },
                "economic": {"estimated_total_tax_revenue_10yr_cad": 180000000.0},
                "sociological": {"residential_population_in_noise_zone": 45000},
                "grid_strain": {"strain_probability": 0.08},
            },
        },
        {
            "name": "malformed_address_edge_case",
            "proposal": ProposalInput(
                address="???",
                province="AB",
                it_load_mw=40.0,
                pue=1.4,
                wue=1.2,
                cooling_type="hybrid",
                facility_type="colocation",
                capex_cad=350.0,
                construction_months=18,
                has_onsite_generation=False,
                renewable_ppa=False,
            ),
            "policy": PolicyDecision(
                recommendation="approve_with_conditions",
                triggered_rules=["developer_due_diligence"],
                selected_clause_ids=["DEVELOPER_FUNDED_DUE_DILIGENCE"],
                policy_summary="approve with due diligence condition",
            ),
            "evidence_pack": {
                "environmental": {
                    "annual_carbon_tonnes": 170000.0,
                    "total_water_litres_per_day": 4512000.0,
                    "pct_of_municipal_daily_supply": 1.1,
                },
                "economic": {"estimated_total_tax_revenue_10yr_cad": 70000000.0},
                "sociological": {"residential_population_in_noise_zone": 38000},
                "grid_strain": {"strain_probability": 0.21},
            },
        },
    ]


def _sessions_dir() -> Path:
    return Path(".railtracks") / "data" / "sessions"


def _list_workflow_session_files() -> set[Path]:
    sessions_dir = _sessions_dir()
    if not sessions_dir.exists():
        return set()
    return {p.resolve() for p in sessions_dir.glob("council_decision_workflow_*.json")}


async def _run_workflow_for_scenario(payload: dict) -> dict:
    proposal: ProposalInput = payload["proposal"]
    policy: PolicyDecision = payload["policy"]
    evidence_pack: dict = payload["evidence_pack"]
    clause_text = {clause_id: CLAUSE_CATALOG[clause_id] for clause_id in policy.selected_clause_ids}

    def _memo_writer_prompt(
        proposal_obj: ProposalInput,
        evidence_obj: dict,
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
        evidence_obj: dict,
        policy_obj: PolicyDecision,
        memo_obj,
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
    async def _workflow() -> dict:
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
        det_ok, det_errors = validate_memo_grounding(draft, evidence_pack, policy, proposal)
        verifier = await rt.call(
            MemoGroundingVerifierAgent,
            _memo_verifier_prompt(proposal, evidence_pack, policy, draft, clause_text),
        )
        if det_ok and verifier.passed:
            return {"verification_passed": True, "repair_attempted": False, "issues": []}

        evidence_with_errors = {**evidence_pack, "validation_errors": [*det_errors, *verifier.issues]}
        repaired = await rt.call(
            MemoWriterAgent,
            _memo_writer_prompt(
                proposal,
                evidence_with_errors,
                policy,
                clause_text,
                validation_errors=[*det_errors, *verifier.issues],
            ),
        )
        repaired_ok, repaired_errors = validate_memo_grounding(repaired, evidence_pack, policy, proposal)
        repaired_verifier = await rt.call(
            MemoGroundingVerifierAgent,
            _memo_verifier_prompt(proposal, evidence_pack, policy, repaired, clause_text),
        )
        return {
            "verification_passed": bool(repaired_ok and repaired_verifier.passed),
            "repair_attempted": True,
            "issues": [*repaired_errors, *repaired_verifier.issues],
        }

    try:
        result, _session = await _workflow()
        return {
            "name": payload["name"],
            "verification_passed": bool(result.get("verification_passed", False)),
            "repair_attempted": bool(result.get("repair_attempted", False)),
            "issues": list(result.get("issues", [])),
            "workflow_error": None,
        }
    except Exception as exc:
        return {
            "name": payload["name"],
            "verification_passed": False,
            "repair_attempted": False,
            "issues": [f"workflow_error: {exc.__class__.__name__}"],
            "workflow_error": str(exc),
        }


def _build_judge_evaluator() -> JudgeEvaluator:
    llm = make_railtracks_llm()
    judge_metrics = [
        LLMMetric(name="groundedness"),
        LLMMetric(name="policy_alignment"),
        LLMMetric(name="clarity"),
    ]
    return JudgeEvaluator(llm=llm, metrics=judge_metrics, reasoning=True)


def _write_outputs(
    out_dir: Path,
    scenario_results: list[dict],
    eval_result,
    session_files: list[str],
    include_judge: bool,
    note: str | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "railtracks_eval_result.json"
    summary_path = out_dir / "railtracks_eval_summary.md"

    if eval_result is None:
        serialized_eval = None
    elif isinstance(eval_result, list):
        serialized_eval = [item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item) for item in eval_result]
    elif hasattr(eval_result, "model_dump"):
        serialized_eval = eval_result.model_dump(mode="json")
    else:
        serialized_eval = str(eval_result)

    payload = {
        "scenario_results": scenario_results,
        "session_files": session_files,
        "judge_enabled": include_judge,
        "note": note,
        "evaluation_result": serialized_eval,
    }
    json_path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")

    passed = sum(1 for s in scenario_results if s["verification_passed"])
    lines = [
        "# Railtracks Workflow Evaluation",
        "",
        f"- Scenarios run: {len(scenario_results)}",
        f"- Scenario verification passed: {passed}/{len(scenario_results)}",
        f"- Judge evaluator enabled: {'yes' if include_judge else 'no'}",
        f"- Session traces evaluated: {len(session_files)}",
        "",
    ]
    if note:
        lines.extend([f"- Note: {note}", ""])
    lines.extend(["## Scenario Outcomes", ""])
    for row in scenario_results:
        issues = "; ".join(row["issues"]) if row["issues"] else "none"
        lines.append(
            f"- `{row['name']}`: passed={row['verification_passed']}, repair_attempted={row['repair_attempted']}, issues={issues}"
        )

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Railtracks memo workflow evaluation across fixed scenarios.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "docs" / "results",
        help="Output directory for evaluation artifacts.",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Run only ToolUseEvaluator (skip JudgeEvaluator if no LLM key available).",
    )
    args = parser.parse_args()

    scenario_payloads = _scenario_payloads()
    before_files = _list_workflow_session_files()
    scenario_results = [asyncio.run(_run_workflow_for_scenario(payload)) for payload in scenario_payloads]
    after_files = _list_workflow_session_files()
    new_files = sorted(str(p) for p in (after_files - before_files))

    include_judge = not args.skip_judge
    note: str | None = None
    eval_result = None

    if new_files:
        try:
            data_points = extract_agent_data_points(new_files)
            evaluators = [ToolUseEvaluator()]
            if include_judge:
                evaluators.append(_build_judge_evaluator())
            eval_result = evaluate(data_points, evaluators, name="council_decision_workflow_eval")
        except Exception as exc:
            note = f"Evaluation skipped due to runtime issue: {exc.__class__.__name__}: {exc}"
    else:
        note = (
            "No new railtracks session files were produced. "
            "This commonly occurs when the configured LLM backend does not support structured outputs."
        )

    _write_outputs(args.out_dir, scenario_results, eval_result, new_files, include_judge, note=note)


if __name__ == "__main__":
    main()
