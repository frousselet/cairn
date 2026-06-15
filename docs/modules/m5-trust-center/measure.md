# TrustCenterMeasure

`trust_center.models.measure.TrustCenterMeasure`

A security measure advertised on the public Trust Center. Unlike certifications, subprocessors and documents, a measure is **free-form curator copy with no link to internal data**, so nothing sensitive can leak through it. It exists to describe, in marketing-friendly terms, the organizational, technical and physical controls the organization has in place.

File: `trust_center/models/measure.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`TCME`**, e.g. `TCME-1`), `django-simple-history` audit trail, and the `trust_center_publication` lifecycle workflow.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto `TCME-N`, unique | Business reference |
| `title` | string | required, max 255 | Measure title (e.g. "Encryption at rest and in transit") |
| `description` | text | optional, blank default | Public-facing description of the measure |
| `icon` | string | max 50, optional, default `bi-shield-check` | Bootstrap Icons name, validated against `^bi-[a-z0-9-]+$` |
| `category` | enum | required, default `organizational` | One of `organizational`, `technical`, `physical` |
| `display_order` | int | `PositiveIntegerField`, default `0` | Render order within the Measures section |
| `workflow_state` | string | indexed | Lifecycle state (`trust_center_publication`) |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `tags` | relation | M2M -> Tag | Free tagging (from `BaseModel`) |

`Meta.ordering = ["display_order", "title"]`.

## Enumerations

### `category` (`MeasureCategory`)

| Value | Description |
|---|---|
| `organizational` | Organizational measures (policies, governance, training, processes) |
| `technical` | Technical measures (encryption, access control, logging, hardening) |
| `physical` | Physical measures (data-center security, access badges, CCTV) |

The categories mirror the ISO/IEC 27002:2022 control attribute "control type", and the public page groups measures by category.

## Computed properties

### `workflow_perm_namespace`

Returns `"trust_center.measure"`, so lifecycle transitions resolve their permission against the `measure` feature.

## Lifecycle

Runs the shared `trust_center_publication` workflow (see [README.md §2.3](README.md#23-the-trust_center_publication-workflow)). Publish / unpublish / archive-from-published require `approve`; archiving a draft / unpublished entry is `update`.

## Publish gate

Because a measure carries **no internal source object**, only the base publication gate applies : `MeasureQuerySet.published()` returns entries whose `workflow_state` is `published`. There is no second source-validity clause (RG-TC-16). The global `is_published` switch is enforced separately at the view layer.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-16 | A measure is free-form curator copy with no internal link; only the base publication gate plus the global switch apply. |
| RG-TC-17 | `icon` must be a Bootstrap Icons name (`^bi-[a-z0-9-]+$`), per the brand iconography rule; `category` is one of `organizational`, `technical`, `physical`. |

## Endpoints

### REST (management, authenticated, `/api/v1/trust-center/`)

- `GET /measures/` : list (search on `title`, `description`; ordering on `display_order`, `title`, `created_at`; `?workflow_state=` filter).
- `POST /measures/`
- `GET /measures/{id}/`
- `PUT/PATCH /measures/{id}/`
- `DELETE /measures/{id}/`
- `POST /measures/{id}/transition/`

### REST (public, `/trust/api/`)

- `GET /trust/api/measures/` : published measures via `PublicMeasureSerializer` (fields: `title`, `description`, `icon`, `category` as its display label). Also included in the aggregate `GET /trust/api/`.

### MCP

- `list_trust_center_measure` / `get_trust_center_measure` / `create_trust_center_measure` / `update_trust_center_measure` / `delete_trust_center_measure`
- `transition_trust_center_measure` / `trust_center_measure_allowed_transitions`

## Permissions

| Codename | Description |
|---|---|
| `trust_center.measure.read` | List / read measures |
| `trust_center.measure.create` | Create a measure |
| `trust_center.measure.update` | Modify a measure (and archive a draft / unpublished one) |
| `trust_center.measure.delete` | Hard-delete a measure |
| `trust_center.measure.approve` | Publish / unpublish / archive a published measure |

## References

- ISO/IEC 27002:2022 control types (organizational / technical / physical).
- Brand guidelines : Bootstrap Icons only (`docs/brand/brand-guidelines.md`).
- [README.md](README.md) : §2.6 (measure rules), §6 (data-leakage safety).
