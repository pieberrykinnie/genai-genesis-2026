from models import CouncilMemo, PolicyDecision

def validate_memo(memo: CouncilMemo, evidence_pack: dict, policy: PolicyDecision) -> tuple[bool, list[str]]:
    errors = []
    
    if not memo.executive_summary or not memo.recommendation_section:
        errors.append("Missing required memo fields.")
        
    if policy.recommendation not in memo.recommendation_section.lower():
        errors.append(f"Recommendation section must explicitly reference '{policy.recommendation}'.")
        
    if len(memo.clause_narratives) > len(policy.selected_clause_ids):
        errors.append("Memo contains more clauses than selected by policy engine.")
        
    return len(errors) == 0, errors
