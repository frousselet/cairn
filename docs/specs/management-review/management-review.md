# ManagementReview

`reports.models.management_review.ManagementReview`

Persistent management review (ISO 27001:2022 clause 9.3) covering its full lifecycle from planning through closure.

Represents a planned or held management review. Persistent root object that replaces the current "ephemeral export" behaviour.

File : `reports/models/management_review.py`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto (prefix `MRVW`), unique | Sequential reference (e.g. `MRVW-1`) |
| `title` | string | required, max 255 | Title (e.g. "Annual management review 2026") |
| `description` | text | optional | Context, purpose of the review |
| `scopes` | relation | M2M → Scope, at least 1 | Scopes covered by the review |
| `frequency` | enum | required | `quarterly`, `semiannual`, `annual`, `exceptional` |
| `period_start` | date | required | Start of the period under review |
| `period_end` | date | required | End of the period under review |
| `planned_date` | date | required | Planned date of the review |
| `held_date` | date | optional | Actual date held |
| `location` | string | optional, max 255 | Location (physical or video conference) |
| `status` | enum | required | `planned`, `in_preparation`, `held`, `closed`, `cancelled` |
| `facilitator` | FK → User | required | Facilitator / minute-taker |
| `approver` | FK → User | optional | Approver (typically top management) |
| `next_review_date` | date | optional | Planned date of the next review |
| `summary` | text | optional | Executive summary written by the facilitator |
| `agenda` | text | optional | Agenda (HTML rich text) |
| `minutes` | text | optional | Detailed minutes (HTML rich text) |
| `snapshot_data` | JSONField | optional | Snapshot of the aggregated data at the time of closure (to freeze auditability) |
| `created_by` | FK → User | auto | Creator |
| `created_at`, `updated_at` | datetime | auto | Traceability |
| `tags` | M2M → Tag | optional | Free-form tagging |

**History** : `django-simple-history` (`HistoricalRecords`) for the audit trail.

**Lifecycle (workflow)** :

```
planned ─► in_preparation ─► held ─► closed
       └──────────────────────────► cancelled
```

Transitions :

- `planned → in_preparation` : the facilitator locks the agenda and triggers data collection.
- `in_preparation → held` : on entry of `held_date`. The entered clause 9.3.2 inputs are frozen in `snapshot_data`.
- `held → closed` : all decisions must have an owner and a due date ; the status switches once the `approver` validates.
- `* → cancelled` : reason required, stored via a comment (cf. [comment.md](comment.md)).

The UI must use the **horizontal stepper** described in `CLAUDE.md` (cf. `compliance/templates/compliance/assessment_detail.html`).

## Extensions to Indicator / IndicatorMeasurement

**No model change**. `IndicatorMeasurement` already exists (`context/models/indicator.py:352`). The spec only requires these measurements to be leveraged on the export side :

- Trend computed over the review period : comparison of the **average of the measurements** `period_start → period_end` vs. the equivalent previous period.
- Computed `trend` marker : `improving`, `stable`, `degrading`, `insufficient_data` (< 2 measurements).
- Computation of **frequency compliance** : expected number of measurements over the period (according to `review_frequency`) vs. the actual number. Reported as `measurement_compliance_pct`.
