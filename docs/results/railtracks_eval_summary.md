# Railtracks Workflow Evaluation

- Scenarios run: 3
- Scenario verification passed: 2/3
- Judge evaluator enabled: yes
- Session traces evaluated: 3

- Note: Evaluation skipped due to runtime issue: ValidationError: 1 validation error for LLMCall
total_cost
  Input should be a valid number [type=float_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.12/v/float_type

## Scenario Outcomes

- `ab_high_load`: passed=True, repair_attempted=False, issues=none
- `qc_lower_risk`: passed=False, repair_attempted=True, issues=Invented numeric claim: capex of 800000.0 CAD in economic_section, actual capex is 800.0 CAD in proposal; Clause narratives misaligned with selected_clause_ids: only one clause narrative is provided, but the narrative matches the selected clause
- `malformed_address_edge_case`: passed=True, repair_attempted=False, issues=none