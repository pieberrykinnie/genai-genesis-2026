# HCI Evaluation: ClearSite Dashboard

## Cognitive Walkthrough

### Task 1: Enter a proposal and run assessment
- Goal: User can submit valid proposal details in under 2 minutes.
- Success cues:
  - Step label indicates they are in "Proposal Intake".
  - Required inputs are visible and grouped by concept.
  - Progress panel confirms system is working after submit.
- Failure checks:
  - Inputs missing units (MW, CAD M, PUE/WUE ranges).
  - Error states are ambiguous or hidden.

### Task 2: Understand where impact applies
- Goal: User can identify municipality/location context immediately.
- Success cues:
  - Location map shows marker tied to returned coordinates.
  - Province and municipality displayed below map.
  - Risk chips summarize top context indicators.
- Failure checks:
  - Blank map without explanation.
  - No evidence of geocoding status.

### Task 3: Interpret impact without technical background
- Goal: User can explain environmental/economic/grid effects in plain language.
- Success cues:
  - Narrative cards use short explanatory sentences.
  - Composite summary is visible and understandable.
- Failure checks:
  - Jargon-heavy blocks without interpretation.
  - Metrics shown without practical implication.

### Task 4: Prepare council negotiation points
- Goal: User can export/discuss policy actions from one screen.
- Success cues:
  - Decision brief includes numbered negotiation actions.
  - Evidence table exposes freshness/source status per dataset.
- Failure checks:
  - No traceability of data status.
  - Ambiguous fallback statuses.

## Heuristic Evaluation Checklist

### Visibility of system status
- [x] Streamed progress with stage + percentage.
- [x] Freshness/evidence table for source visibility.

### Match between system and real world
- [x] Uses municipal wording (proposal, council decision, negotiation actions).
- [x] Includes units and plain-language statements.

### User control and freedom
- [x] Inputs can be edited and re-submitted quickly.
- [ ] Add reset-to-default button in next pass.

### Consistency and standards
- [x] Four-step flow is consistent with page sections.
- [x] Reused card/field patterns across sections.

### Error prevention and recovery
- [x] Backend errors are displayed in-page.
- [x] Map explains missing key state instead of failing silently.

### Recognition over recall
- [x] Stepper keeps current phase visible.
- [x] Risks summarized as chips and narrative blocks.

### Aesthetic and minimalist design
- [x] High-signal sections only (intake, map, impact, decision).
- [x] Redundant technical text removed from primary flow.

## Critical UX fixes applied in this pass
1. Replaced single raw-output layout with step-anchored workflow.
2. Added plain-language interpretation beside numeric outputs.
3. Added explicit evidence/freshness panel for trust and governance.
4. Added map context and fallback explanation for missing map key.
