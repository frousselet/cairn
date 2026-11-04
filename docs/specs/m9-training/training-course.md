# TrainingCourse

`training.models.course.TrainingCourse`

An entry of the training catalogue : an awareness module, a phishing simulation, a technical or regulatory training. It says what is taught, how, for how long, by whom, and how long a completion stays valid (RG-TRN-02). It is delivered through [campaigns](training-campaign.md) and satisfies [competencies](competency.md).

File: `training/models/course.py`

`ScopedModel` subclass : UUID PK, `reference` (prefix **`CRSE`**), `scopes`, `tags`, `version`, `created_by`, history. `LIFECYCLE_NAME = "training_course"`. `workflow_perm_namespace = "training.course"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `title` | string | required, max 255 | e.g. `Annual security awareness` |
| `description` | text | optional | Objectives and content outline |
| `course_type` | enum | required, default `awareness` | `awareness`, `phishing_simulation`, `technical`, `regulatory`, `onboarding`, `management` |
| `delivery` | enum | required, default `elearning` | `elearning`, `classroom`, `webinar`, `simulation`, `reading` |
| `duration_minutes` | integer | optional, 1 to 6000 | Expected duration |
| `provider` | string | optional, max 255 | Internal team or external organisation |
| `provider_supplier` | relation | FK -> `assets.Supplier`, `SET_NULL`, optional | When the provider is a referenced supplier |
| `validity_months` | integer | optional, 1 to 60 | RG-TRN-02 : empty means never expires |
| `pass_mark` | integer | optional, 0 to 100 | RG-TRN-09 |
| `allows_self_attestation` | boolean | default `false` | RG-TRN-08 : addressees may declare completion themselves |
| `attestation_statement` | string | max 500, default *"I have completed {title}."* | Snapshotted on a self-attested row |
| `owner` | relation | FK -> User, `SET_NULL`, optional | Accountable for the course |
| `requirements` | M2M | `compliance.Requirement`, reverse `training_courses` | A.6.3, clause 7.2 / 7.3, NIS2 article 20.2 |
| `policies` | M2M | `documents.Policy`, reverse `training_courses` | The policies or charters the course teaches |
| `workflow_state` | string | default `draft` | `training_course` lifecycle |

Reverse accessors : `campaigns`, `competencies` (from `Competency.satisfied_by`).

## Deletion

Only a `draft` course without campaigns (RG-TRN-04).

## References

- ISO/IEC 27001:2022 clause 7.2, 7.3, A.6.3; NIS2 article 20.2, 21.2 g
- [README.md](README.md) : RG-TRN-01, RG-TRN-02, RG-TRN-08, RG-TRN-09
