import railtracks as rt
from models import ProposalInput, ImpactAssessment, CouncilMemo
from orchestrator.agents import MemoWriterAgent, MemoInput
from orchestrator.validators import validate_memo
from policy.clause_catalog import CLAUSE_CATALOG
from policy.engine import select_policy
# Imports below are placeholders depending on project ingestion details 
# and actual implemented calculators, they mock the spec flow
# from ingestion.proposal_normalize import ingest_or_extract
# from data_sources.fetching import fetch_public_context
# from calculator.scoring import run_calculations
# from ml.grid_strain.predict import predict_grid_strain
# from ml.site_fit.predict import predict_site_fit

class AsyncMock:
    pass

@rt.session(name="assess_proposal")
async def assess_flow(user_payload: dict):
    await rt.broadcast("proposal_ingest")
    # proposal = await ingest_or_extract(user_payload)
    proposal = ProposalInput(**user_payload)

    await rt.broadcast("fetching_public_data")
    # public_context = fetch_public_context(proposal)

    await rt.broadcast("running_calculations")
    # evidence = run_calculations(proposal, public_context)
    evidence = {
        "environmental": {"carbon_score": "amber", "water_score": "amber", "grid_score": "amber", "pct_of_municipal_daily_supply": 5},
        "economic": {"jobs_gap": 0},
        "sociological": {"sociological_score": "amber", "indigenous_flag": False, "residential_population_in_noise_zone": 500}
    }

    await rt.broadcast("running_grid_model")
    # evidence["grid_strain"] = predict_grid_strain(proposal, public_context)
    evidence["grid_strain"] = {
        "strain_probability": 0.4, "rate_increase_probability": 0.2, "predicted_strain_level": "moderate", "confidence": 0.9, "model_version": "v1", "top_features": []
    }

    await rt.broadcast("running_site_fit_model")
    # evidence["site_fit"] = predict_site_fit(proposal, public_context)
    evidence["site_fit"] = {
        "site_fit_probability": 0.6, "site_fit_band": "moderate", "confidence": 0.9, "model_version": "v1", "top_features": [], "nearest_similar_sites": []
    }

    await rt.broadcast("selecting_policy")
    policy = select_policy(evidence)

    await rt.broadcast("writing_memo")
    memo = await rt.call(
        MemoWriterAgent,
        MemoInput(
            proposal=proposal,
            evidence_pack=evidence,
            policy_decision=policy,
            clause_text={k: CLAUSE_CATALOG[k] for k in policy.selected_clause_ids},
        )
    )

    await rt.broadcast("validating_memo")
    ok, errors = validate_memo(memo, evidence, policy)
    if not ok:
        evidence_with_errors = {**evidence, "validation_errors": errors}
        memo = await rt.call(
            MemoWriterAgent,
            MemoInput(
                proposal=proposal,
                evidence_pack=evidence_with_errors,
                policy_decision=policy,
                clause_text={k: CLAUSE_CATALOG[k] for k in policy.selected_clause_ids},
            )
        )

    # return build_response(proposal, evidence, policy, memo)
    return {
        "proposal": proposal.model_dump(),
        "policy": policy.model_dump(),
        "memo": memo.model_dump()
    }
