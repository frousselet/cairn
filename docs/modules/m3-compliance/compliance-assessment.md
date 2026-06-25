# ComplianceAssessment

`compliance.models.assessment.ComplianceAssessment`

Compliance assessment campaign, **multi-framework**, covering one or more [Framework](framework.md).

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CAST-N`, unique | Business reference |
| `scopes` | relation | M2M -> Scope | ISMS scopes covered |
| `frameworks` | relation | M2M -> Framework | Frameworks assessed in this campaign. The implementation is multi-framework (a single assessment can cover ISO 27001 + GDPR simultaneously), an accepted divergence from the original single-framework spec (see the documented gap below). |
| `name` | string | required, max 255 | Title of the assessment (e.g. "Annual assessment 2026") |
| `description` | text | optional, HTML | Context and objective of the assessment |
| `limitations` | text | optional, HTML | Limitations / excluded scope / reservations of the assessment. Replaces the `methodology` field of the original spec; the methodology is instead carried at the framework level or in the audit documentation. |
| `assessment_start_date` | date | optional | Start of the audit period |
| `assessment_end_date` | date | optional | End of the audit period. The original spec had only a single `assessment_date`; the implementation uses a period to capture audits that span several days / weeks. |
| `assessor` | relation | FK -> User, required, PROTECT | Lead assessor |
| `overall_compliance_level` | decimal(5,2) | calculated, 0-100 | Overall compliance level (%). Recalculated by `recalculate_counts()`. Excludes `NOT_APPLICABLE` from both the numerator and the denominator (issue #46). |
| `total_requirements` | integer | calculated | Total number of applicable requirements covered |
| `compliant_count` | integer | calculated | Number of `compliant` requirements |
| `major_non_conformity_count` | integer | calculated | Number of `major_non_conformity` requirements |
| `minor_non_conformity_count` | integer | calculated | Number of `minor_non_conformity` requirements |
| `observation_count` | integer | calculated | Number of `observation` requirements |
| `improvement_opportunity_count` | integer | calculated | Number of `improvement_opportunity` requirements |
| `strength_count` | integer | calculated | Number of `strength` requirements |
| `evaluated_count` | integer | calculated | Number of `evaluated` requirements (placeholder) |
| `not_assessed_count` | integer | calculated | Number of `not_assessed` requirements |
| `not_applicable_count` | integer | calculated | Number of `not_applicable` requirements |
| `status` | enum | required, default `draft` | See "Lifecycle" below |
| `results` | reverse FK | O2M -> AssessmentResult | Per-requirement results |
| `findings` | reverse M2M | <- compliance.Finding (`Finding.assessment`) | Attached audit findings |
| `is_approved` / `approved_by` / `approved_at` | bool / FK -> User / datetime | optional | Approval indicator, an orthogonal axis to `status` (see "Lifecycle") |
| `version` | int | auto-incremented | Bumped on each major change |
| `tags` | relation | M2M -> Tag | |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | |

## Lifecycle

`status` follows the actual workflow: `draft -> planned -> in_progress -> completed -> closed`, plus `cancelled` as a terminal branch reachable from `draft` and `planned`. Once `completed` or `closed`, the assessment can no longer move backwards.

```text
  draft -> planned -> in_progress -> completed -> closed
    \         \
     +---------+----> cancelled  (terminal)
```

| Status | Meaning |
|---|---|
| `draft` | Configuration draft: business fields editable, not yet launched |
| `planned` | Configuration validated, scheduled, awaiting start |
| `in_progress` | In progress: the `AssessmentResult` entries are being filled in by the assessor |
| `completed` | Assessment conducted, results entered, awaiting validation / closure |
| `closed` | Finished and closed (terminal). The RC-06 carry-over (`recalculate_counts`) is triggered here |
| `cancelled` | Assessment cancelled (terminal). No carry-over is triggered |

### Validation and approval

`is_approved` is an **orthogonal axis** to `status`, captured by the `approve_compliance_assessment` action (REST `POST /assessments/<uuid>/approve/`, MCP `approve_compliance_assessment`). Approval can be set at any time (typically when the assessment is `completed` or `closed`) and represents the formal validation of the result by an approver (CISO, DPO, executive committee).

The `validated` status listed in the original M3 spec §2.4 does not exist in the implemented enum: "validation" is carried by the pair (`status=closed`, `is_approved=true`). This separation was chosen to allow:

- **closing** an assessment without formally validating it (recurring internal audit whose results are consumed immediately without an approver's signature);
- **approving** an assessment across several successive levels (the auditor moves it to `completed`, the CISO moves it to `closed`, the DPO or the committee approves it later via `is_approved`).

The `archived` status from the original spec was not carried over either: `closed` plays the terminal role, and a potential need for explicit archiving can be added later through a flag or a separate status without breaking the current workflow.

| Original spec | Current implementation |
|---|---|
| `draft` | `draft` |
| `in_progress` | `planned` or `in_progress` (the implementation distinguishes planning from execution) |
| `completed` | `completed` |
| `validated` | `closed` + `is_approved=true` |
| `archived` | `closed` (terminal). No dedicated status for now |

### Allowed transitions

`ComplianceAssessment.transition_to(new_status)` validates the transition against `ASSESSMENT_STATUS_TRANSITIONS` (`compliance/constants.py`):

```text
draft        -> planned, cancelled
planned      -> in_progress, cancelled
in_progress  -> completed
completed    -> closed
closed       -> (terminal)
cancelled    -> (terminal)
```

The REST API `POST /assessments/<uuid>/transition/` and the MCP `update_compliance_assessment` (via the `status` field) enforce these rules. An unauthorized transition raises a `ValueError` reformatted as a `400 Bad Request`.

### Side effects per transition

- `in_progress -> completed`: resets the `AssessmentResult.compliance_status` entries that remained `EVALUATED` without an attached finding to `NOT_ASSESSED` (consistency: a "planned assessment" placeholder that received no finding reverts to "not assessed"). Calls `recalculate_counts()`.
- `completed -> closed`: triggers `recalculate_counts()` (RC-06). The `AssessmentResult` entries are carried over to the `Requirement` records; `Framework.last_assessment_date` is updated with `assessment_end_date`.

### RC-06 trigger

The carry-over of results onto requirements (RC-06) is triggered on **closure** (`completed -> closed`), not on approval. `approve_compliance_assessment` triggers no calculation, it is purely a validation signature. This separation makes it possible to review and correct a closed assessment before approving it, without the approval having to recompute anything.

## Divergences from the original spec

The M3 spec §2.4 described a single-framework assessment, dated to a single date, carrying a `methodology` field and without an explicit link to the scope. The implementation has evolved along these four axes; the choices are settled.

### Multi-framework (`frameworks` M2M)

An assessment can cover several frameworks simultaneously. Use case: an annual ISO 27001 + GDPR + sector-specific standard audit (e.g. HDS for healthcare) is a single campaign, not three. It allows the field work to be shared (the evidence collected for ISO 27001 §A.5.34 also serves GDPR Article 32) and a single audit window to be shared with the auditees.

**Impact on RC-06.** On closure, `recalculate_counts()` propagates each `AssessmentResult` to its target `Requirement`, regardless of the framework that requirement belongs to. All attached frameworks thus have their `Framework.compliance_level` recalculated, and their `Framework.last_assessment_date` updated with the campaign's `assessment_end_date`.

On the query side: `assessment.frameworks.all()` enumerates the covered frameworks; `assessment.results.all()` enumerates the results across all frameworks; to scope by framework use `assessment.results.filter(requirement__framework=fw)`.

### Audit period (`assessment_start_date` / `assessment_end_date`)

The original spec had only a one-off `assessment_date`. The implementation uses a **period** because an audit typically spans several days (field cycle + documentary review + debrief), sometimes several weeks for heavy frameworks. The `assessment_end_date` serves as the reference for freshness (`Framework.last_assessment_date` takes this value on closure); the `assessment_start_date` documents the window start for audit exports.

### `limitations` instead of `methodology`

The original spec had a `methodology` field to describe the audit method. The implementation replaced it with `limitations` (reservations, exclusions, scope not covered). The methodology is instead carried at the level of the attached audit documentation (evidence template, audit plan) or at the Framework level (an ISO 27001 framework implies a known methodology, no need to duplicate it for each campaign). `limitations` captures what must appear in the audit report: "the server room at site B could not be inspected", "the scope excludes the subsidiaries acquired in 2025".

### Link to the scope (`scopes` M2M)

The assessment is a `ScopedModel` and accepts `scope_ids` like all other domain entities (cross-cutting attachment RG-01). It makes it possible to compartmentalize audits by ISMS scope: an audit of the "France" scope does not pollute the KPIs of the "Germany" scope. A cross-cutting audit can remain without a scope (empty list).

## AssessmentResult

`compliance.models.assessment.AssessmentResult`

Assessment result for a requirement within a campaign. One result per `(assessment, requirement)` pair; the uniqueness constraint is encoded at the database level.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `assessment_id` | relation | FK -> ComplianceAssessment, required, cascade | Parent assessment |
| `requirement_id` | relation | FK -> Requirement, required, cascade | Assessed requirement |
| `compliance_status` | enum | required, default `not_assessed` | See "Compliance statuses" below |
| `compliance_level` | integer | default 0, 0-100 | Compliance level (%) |
| `finding` | text | optional, HTML | Audit finding. Replaces the `gaps` / `observations` pair of the original spec; the merge matches actual usage: an assessor writes a single block that describes both the gaps and the contextual observations. |
| `auditor_recommendations` | text | optional, HTML | Recommendations formulated by the auditor. Field added by the implementation to capture improvement leads without duplicating the `compliance_finding` of the `Requirement`. |
| `evidence` | text | optional, HTML | Evidence observed (document citations, screenshots, etc.) |
| `assessed_by` | relation | FK -> User, required, PROTECT | Assessor |
| `assessed_at` | datetime | required | Date and time of the assessment |
| `attachments` | reverse FK | O2M -> [AssessmentResultAttachment](attachment.md) | Attachments (documentary evidence) |
| `created_at` / `updated_at` | datetime | auto | |

> Uniqueness constraint: the (`assessment_id`, `requirement_id`) pair must be unique.

### Compliance statuses

`AssessmentResult.compliance_status` shares **exactly the same 11-value enumeration** as `Requirement.compliance_status`: `compliance.constants.ComplianceStatus`. See [requirement.md § Compliance statuses](requirement.md#compliance-statuses) for the full table and the mapping of audit statuses (`major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`, `evaluated`) to the conformance values used by the RC-01 and RC-02 aggregates.

The consistency between the two enumerations is intentional: an audit produces a result whose `compliance_status` is directly carried over to the target requirement without an intermediate mapping table (see RC-06 below).

### Divergences from the original spec

The M3 spec §2.5 listed `gaps` and `observations` as two distinct fields, plus a `compliance_status` reduced to 5 values (`not_assessed`, `non_compliant`, `partially_compliant`, `compliant`, `not_applicable`). The implementation has evolved to align the result with the ISO 19011 audit vocabulary and with the Audits module:

- `gaps` + `observations` are merged into a single `finding` field (same reasons as `Requirement.compliance_finding`, see #39).
- An `auditor_recommendations` field is added to capture recommendations distinctly from the finding (the `finding` describes what is, the `auditor_recommendations` what should be done).
- `compliance_status` is extended to the 6 audit values (`evaluated`, `major_non_conformity`, `minor_non_conformity`, `observation`, `improvement_opportunity`, `strength`) in addition to the 5 conformance values.

The decision to align these divergences was settled with the resolution of #44: the spec now follows the implementation.

### RC-06 (result -> requirement carry-over)

On closure / validation of a `ComplianceAssessment`, `recalculate_counts()` propagates each `AssessmentResult` to the targeted requirement:

1. If `result.compliance_status` is `not_assessed`, the target requirement is **not** modified (preservation of prior assessments, issue #45 resolved).
2. If `result.compliance_status` is `evaluated` ("planned assessment" placeholder), the last **actually assessed** result for this requirement across any assessment of the same framework is looked up in its history and carried over instead.
3. Otherwise, `result.compliance_status` and `result.compliance_level` are carried over as is to the requirement; `Requirement.last_assessment_date` and `Requirement.last_assessed_by` are updated with the result's values.

The shared enum guarantees that no mapping is necessary between result and requirement: a `major_non_conformity` on the result side becomes a `major_non_conformity` on the requirement side, which is then aggregated as `non_compliant` in the RC-01 / RC-02 averages via the mapping documented on the Requirement side.

### Link with the Audits module

The `Finding` records of the Audits module can be attached to an `AssessmentResult` via `Finding.requirements`. The `ComplianceAssessment.apply_findings_to_results()` method then aligns the `compliance_status` of each result with the most severe status among the attached findings (according to `FINDING_SEVERITY_ORDER` in `compliance.constants`). This allows an audit to produce findings whose severity mechanically overrides the status of a result without manual entry.
