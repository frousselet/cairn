# Requirement

`compliance.models.requirement.Requirement`

Individual requirement extracted from a [Framework](framework.md), the elementary unit of compliance assessment.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `framework_id` | relation | FK -> Framework, required | Parent framework |
| `section_id` | relation | FK -> Section, optional | Attached section |
| `requirement_number` | string | optional, max 100 | Number / business reference of the requirement (e.g. "A.5.1.1", "Art. 32.1.a"). Unique per framework when set. |
| `reference` | string | auto-generated `REQT-N`, unique | Internal reference |
| `name` | string | required, max 500 | Short title of the requirement |
| `description` | text | required | Full text of the requirement |
| `guidance` | text | optional | Implementation guidance / interpretation notes |
| `type` | enum | required | `mandatory`, `recommended`, `optional` |
| `category` | enum | optional | `organizational`, `technical`, `physical`, `legal`, `human`, `other` |
| `is_applicable` | boolean | required, default `true` | Applicable to the scope. Derived automatically from the associated risks (read-only) when the framework has `applicability_managed_by_risks` enabled: see `docs/modules/m3-compliance/framework.md` |
| `applicability_justification` | text | optional | Justification of non-applicability (SoA). Filled in automatically in risk-driven applicability mode |
| `compliance_status` | enum | required, default `not_assessed` | See the "Compliance statuses" section below |
| `compliance_level` | integer | default 0, 0-100 | Compliance level (%). Propagated from the `AssessmentResult` by `assessment.recalculate_counts()` |
| `compliance_evidence` | text | optional | Evidence / elements of compliance |
| `compliance_finding` | text | optional | Audit finding / gaps (formerly `compliance_gaps` in the original spec, renamed to align with the audit vocabulary of the Audits module) |
| `last_assessment_date` | date | optional | Date of the last assessment |
| `last_assessed_by` | relation | FK -> User, optional | Last assessor |
| `owner_id` | relation | FK -> User, optional | Owner of compliance remediation |
| `priority` | enum | optional | `low`, `medium`, `high`, `critical` |
| `target_date` | date | optional | Target date for compliance |
| `linked_assets` | relation | M2M -> EssentialAsset | Essential assets concerned |
| `linked_stakeholder_expectations` | relation | M2M -> StakeholderExpectation | Associated stakeholder expectations |
| `linked_risks` | reverse M2M | -> Risk via `Risk.linked_requirements` | Associated risks (fed from the Risk side) |
| `mapped_requirements` | relation | M2M via [`RequirementMapping`](requirement-mapping.md) | Requirements from other frameworks mapped |
| `status` | enum | required, default `active` | `active`, `deprecated`, `superseded` |
| `is_approved` / `approved_by` / `approved_at` | bool / FK -> User / datetime | optional | Standard approval workflow |
| `version` | int | auto-incremented | Bumped on each major change |
| `tags` | relation | M2M -> Tag | |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | |

> Uniqueness constraint: `(framework_id, requirement_number)` when `requirement_number` is non-empty.

## Compliance statuses

The `compliance_status` enumeration brings together two families of values: the simple compliance statuses (the 5 from the original ISO spec) and the audit statuses (from the Audits module, ISO 19011 and internal ISMS conventions). The two families deliberately coexist within the same enumeration: an audit produces a finding with an audit status, and that status directly serves as the `compliance_status` on the assessed requirement via the RC-06 carry-over. Maintaining two enumerations in mirror generated friction (double entry, internal mapping table, audit status invisible outside audits); a single enumeration serves both modules.

### Simple compliance statuses

| Value | Meaning |
|---|---|
| `not_assessed` | Requirement not yet assessed. Default value on creation |
| `non_compliant` | Non-compliant. Triggers RC-05 (regulatory alert if the framework is `is_mandatory`) |
| `partially_compliant` | Partially compliant. The compliant portion is captured by `compliance_level` |
| `compliant` | Compliant |
| `not_applicable` | Not applicable to the scope. Excluded from the RC-01 / RC-02 averages (cf. ISO 27001 SoA CHANGELOG) |

### Audit statuses

From the Audits module. They allow a more precise `compliance_status` when the assessment is conducted within a formal audit.

| Value | Meaning | Implicit compliance mapping |
|---|---|---|
| `evaluated` | Assessment planned but not yet concluded (placeholder). Treated as `not_assessed` in the aggregates, with a fallback to the previous assessment. | `not_assessed` (placeholder) |
| `major_non_conformity` | Major non-conformity (systemic failure, ISO 19011). Critical alert. | `non_compliant` |
| `minor_non_conformity` | Minor non-conformity (one-off failure). | `partially_compliant` |
| `observation` | Neutral observation, no failure found but a point of attention. | `compliant` |
| `improvement_opportunity` | Improvement opportunity. No non-conformity, optimization suggestion. | `compliant` |
| `strength` | Strength noted by the auditor. | `compliant` |

The implicit mapping (right-hand column) is used to compute the aggregated `compliance_level` and the dashboard counters: a `major_non_conformity` status contributes to the non-conformity rate, a `strength` contributes to the compliance rate.

## Effect of each status on the calculations

### RC-01 (overall level of a framework)

`Framework.recalculate_compliance` reads `compliance_status` and `compliance_level` directly on each applicable `Requirement`:

- `not_applicable` is excluded (numerator and denominator, SoA convention).
- `not_assessed` and `evaluated` count as `compliance_level = 0` (except for the fallback handled by `recalculate_counts` which injects the last useful assessment).
- The other statuses contribute their `compliance_level` (0-100).

### RC-02 (level of a section)

Identical to RC-01, scoped to the section. Recursively includes the subsections: the average of the parent section incorporates the levels of the children.

### RC-04 ("not reviewed" alert)

A `compliant` requirement that has had no `last_assessment_date` for more than N days (configurable, default 365) is listed in the "Stale compliance" panel. The audit statuses `observation`, `improvement_opportunity` and `strength` take part in RC-04 in the same way as `compliant` (they are mapped to compliant).

### RC-05 (regulatory alert)

A `non_compliant` or `major_non_conformity` or `minor_non_conformity` requirement on an `is_mandatory=true` framework triggers the critical regulatory non-compliance alert. `partially_compliant` produces a warning-level alert.

### RC-06 (carry-over of audit result -> requirement)

On closure of an assessment (`ComplianceAssessment.recalculate_counts`), each `AssessmentResult` propagates its `compliance_status` and `compliance_level` to the targeted requirement. `not_assessed` results are not carried over (cf. #45 resolved): the prior value of the requirement is preserved. The `evaluated` result is resolved via a fallback to the last effective assessment.

## Articulation with the Audits module

The Audits module (`audits/` on the code side) produces `Finding` records linked to `ComplianceAssessment` records. The type of a finding (`finding_type`: `compliant`, `non_compliant`, `partially_compliant`, `major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`, `not_applicable`) is the same enumeration as `compliance_status` on the Requirement side and `compliance_status` on the AssessmentResult side, which eliminates the mapping friction between the two modules. When a finding is attached to an `AssessmentResult` and the `apply_findings_to_results()` method is called, the `compliance_status` of the result is aligned with the most severe status among the attached findings (according to `FINDING_SEVERITY_ORDER` defined in `compliance.constants`).

## Business rules

| ID | Rule |
|---|---|
| RG-REQ-01 | `(framework_id, requirement_number)` is unique when `requirement_number` is non-empty. |
| RG-REQ-02 | Changing the `compliance_status` or the `compliance_level` of a requirement directly triggers the `post_save` signal that refreshes the owning section, its ancestors and the framework (issue #41 resolved). |
| RG-REQ-03 | `is_applicable=false` must be accompanied by a non-empty `applicability_justification`; this rule is documented but not blocking at the model level (checked in the UI). |
| RG-REQ-04 | During the RC-06 carry-over, a `not_assessed` result does not overwrite the existing `compliance_status` (preservation of prior assessments, issue #45 resolved). |
| RG-REQ-05 | `compliance_finding` is the canonical name of the field (former `compliance_gaps` from the original spec, renamed to align with the audit vocabulary). |
| RG-REQ-06 | If the framework has `applicability_managed_by_risks` enabled, `is_applicable` is derived automatically: `true` as soon as at least one associated risk is in a state counted in reports (`core.workflow.reportable`), `false` otherwise. The `is_applicable` / `applicability_justification` fields are then read-only (any write is ignored) and recalculated via signals (association/dissociation of a risk, state change or deletion of a risk, enabling of the option). |
