from models import PolicyDecision

def select_policy(evidence: dict) -> PolicyDecision:
    clauses = []
    rules = []

    if evidence["grid_strain"]["strain_probability"] >= 0.55:
        clauses += ["GRID_COST_SHARE", "PEAK_CURTAILMENT_PLAN", "ANNUAL_TRANSPARENCY_REPORT"]
        rules.append("high_grid_strain")

    if evidence["environmental"]["water_score"] == "red" or evidence["environmental"]["pct_of_municipal_daily_supply"] >= 10:
        clauses += ["WATER_USE_CAP", "WATER_REPLENISHMENT", "SUBSIDY_CLAWBACK"]
        rules.append("high_water_burden")

    if evidence["sociological"]["indigenous_flag"]:
        clauses += ["INDIGENOUS_CONSULTATION", "ANNUAL_TRANSPARENCY_REPORT"]
        rules.append("indigenous_consultation_required")

    if evidence["site_fit"]["site_fit_probability"] < 0.35:
        clauses += ["DEVELOPER_FUNDED_DUE_DILIGENCE"]
        rules.append("low_site_fit")

    if evidence["sociological"]["residential_population_in_noise_zone"] > 1000:
        clauses += ["NOISE_ABATEMENT"]
        rules.append("noise_exposure")

    jobs_gap = evidence["economic"].get("jobs_gap", 0)
    if jobs_gap > 0:
        clauses += ["LOCAL_HIRING_PLAN"]
        rules.append("jobs_promise_gap")

    clauses = sorted(list(set(clauses)))

    red_count = sum([
        evidence["environmental"]["carbon_score"] == "red",
        evidence["environmental"]["water_score"] == "red",
        evidence["environmental"]["grid_score"] == "red",
        evidence["sociological"]["sociological_score"] == "red",
        evidence["grid_strain"]["strain_probability"] >= 0.75,
        evidence["site_fit"]["site_fit_probability"] < 0.20,
    ])

    if red_count >= 4:
        recommendation = "reject"
    elif red_count >= 2:
        recommendation = "defer"
    elif len(clauses) > 0:
        recommendation = "approve_with_conditions"
    else:
        recommendation = "approve"

    return PolicyDecision(
        recommendation=recommendation,
        triggered_rules=rules,
        selected_clause_ids=clauses,
        policy_summary=f"{recommendation} based on {len(rules)} triggered rule(s)."
    )
