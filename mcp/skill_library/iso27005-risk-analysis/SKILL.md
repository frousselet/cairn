---
name: iso27005-risk-analysis
description: Run an ISO/IEC 27005 information security risk analysis in Cairn, from the risk criteria to the treatment plans and the risk register. Use it when the user asks to assess, analyse, score or treat information security risks.
---

# ISO 27005 risk analysis

Follow the order of ISO/IEC 27005 : criteria, identification, analysis,
evaluation, treatment, acceptance. `help(topic="risks")` gives every field
and value used below.

## 1. Risk criteria

`list_risk_criterias` : reuse the criteria in force when there are some. Only
when there are none, create them with `create_risk_criteria`, then their
likelihood and impact scales and their risk levels (see the risks topic of
`help`).

## 2. The assessment

`create_risk_assessment(name, risk_criteria_id, methodology="iso27005", scope_ids)`
frames the exercise. Move it forward with `transition_risk_assessment`, after
`risk_assessment_allowed_transitions`.

## 3. Identification

- The assets come from `list_essential_assets` and `list_support_assets`.
- The threats from `list_threats`, the vulnerabilities from
  `list_vulnerabilitys`. Create a missing one with `create_threat` or
  `create_vulnerability`.

## 4. Analysis

For each pair of a threat and a vulnerability that matters, call
`create_iso27005_risk(assessment_id, threat_id, vulnerability_id,
threat_likelihood, vulnerability_exposure, impact_confidentiality,
impact_integrity, impact_availability, existing_controls)`. Cairn computes
the likelihood, the impact and the level from the criteria. Then
`consolidate_iso27005_risk` turns an analysis into a risk of the register.

## 5. Evaluation and treatment

- `list_risks(assessment_id=...)` : decide each risk's `treatment_decision`
  (accept, mitigate, transfer, avoid) with `update_risk`.
- For a risk to mitigate : `create_risk_treatment_plan(risk_id, name,
  owner_id, target_date)`, then its actions.
- Record the reason of the decision in `treatment_justification`.
- For a risk to accept : `create_risk_acceptance(risk_id, accepted_by_id,
  justification, valid_until)`; it takes effect through
  `transition_risk_acceptance`, which asks for the approval permission.

## 6. Results

`generate_iso27005_report` and `generate_risk_register` produce the
documents. They may answer with a task : wait for it to complete.

## Rules

- Never invent a likelihood or an impact : ask the user, or state the
  assumption and record it in `existing_controls` or `treatment_justification`.
- A score is the criteria's : do not compute one by hand.
