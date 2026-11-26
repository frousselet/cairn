---
name: compliance-assessment
description: Prepare and run a compliance assessment (an internal audit) against a framework in Cairn, record the results and findings, and produce the audit report and the Statement of Applicability. Use it when the user asks to audit, assess compliance with or measure the gap to ISO 27001, NIS2, GDPR or another framework.
---

# Compliance assessment

`help(topic="compliance")` gives every field and value used below.

## 1. The framework

`list_frameworks` : the framework must exist and be validated. Its
requirements are read with `list_requirements(framework_id=...)`, and its
current coverage with `get_framework_compliance_summary(id)`.

## 2. The assessment

`create_compliance_assessment(name, framework_ids, assessor_id)` creates the
assessment and one result per requirement of the frameworks. Plan it, then
start it, by updating it as the compliance topic of `help` describes.

## 3. The results

For each requirement, `list_assessment_results(assessment_id=...)` then
`update_assessment_result(id, compliance_status, evidence)`. The evidence is
what was seen, by whom, when : never a conclusion without its source.

## 4. The findings

A gap is a finding : `create_finding(assessment_id, finding_type,
description, evidence, recommendation, requirement_ids)`. A major or minor
nonconformity leads to an action plan : `create_action_plan(name, priority,
owner_id, target_date, gap_description, remediation_plan)`.

## 5. The report

Once the assessment is completed or closed, `generate_audit_report(assessment_id)`.
`generate_soa_report(framework_ids)` produces the Statement of
Applicability. Both may answer with a task : wait for it to complete.

## Rules

- A result is marked compliant only on evidence the user gave or a record of
  Cairn shows. Otherwise ask, or leave it unassessed.
- Do not close a finding or an action plan on the user's behalf : propose it.
