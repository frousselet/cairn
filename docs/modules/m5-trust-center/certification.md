# TrustCenterCertification

`trust_center.models.certification.TrustCenterCertification`

A `compliance.Framework` published on the public Trust Center as a certification badge. The entry references the internal framework through a `PROTECT` foreign key but carries its own public-only label and description, so internal framework fields never reach the public surface.

File: `trust_center/models/certification.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`TCCE`**, e.g. `TCCE-1`), `django-simple-history` audit trail, and the `trust_center_publication` lifecycle workflow.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto `TCCE-N`, unique | Business reference |
| `framework` | relation | FK -> `compliance.Framework`, `PROTECT`, required | The internal framework surfaced as a certification. `related_name="trust_center_entries"`. |
| `public_label` | string | required, max 255 | Public-facing name of the certification (e.g. "ISO/IEC 27001:2022") |
| `public_description` | text | optional, blank default | Public-facing description / context |
| `show_percentage` | boolean | required, default `True` | Per-item toggle for the compliance percentage. Combined with the global `TrustCenterSettings.show_compliance_percentages`. |
| `display_order` | int | `PositiveIntegerField`, default `0` | Render order within the Certifications section |
| `workflow_state` | string | indexed | Lifecycle state (`trust_center_publication`); see below |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `tags` | relation | M2M -> Tag | Free tagging (from `BaseModel`) |

`Meta.ordering = ["display_order", "public_label"]`.

## Computed properties

### `public_compliance_level`

Returns the **rounded integer** compliance percentage, or `None` when it must be hidden. It is `None` when:

- the per-item `show_percentage` is off, OR
- the global `TrustCenterSettings.show_compliance_percentages` is off, OR
- `Framework.compliance_level` is missing / non-numeric (returns `None` rather than raising).

Otherwise it is `round(float(self.framework.compliance_level))`. This is the only numeric value the public certification serializer exposes, and only when both toggles are on (RG-TC-12 / RG-TC-13).

### `workflow_perm_namespace`

Returns `"trust_center.certification"`, so the lifecycle transitions resolve their permission action against the `certification` feature (e.g. the Publish transition needs `trust_center.certification.approve`).

## Lifecycle

Runs the shared `trust_center_publication` workflow : `draft` (initial) -> `published` (live) <-> `unpublished` -> `archived` (terminal branch). Only `published` is live on the public page. Publish / unpublish / archive-from-published require the `approve` action; archiving a draft / unpublished entry is `update`. See [README.md §2.3](README.md#23-the-trust_center_publication-workflow) and [governance/workflow.md](../governance/workflow.md).

## Publish gate (dual gate)

`CertificationQuerySet.published()` returns an entry only when **both** conditions hold:

1. its `workflow_state` is `published` (the publication state), AND
2. its `framework.workflow_state` is in the framework's reportable states (the framework is still validated / active).

So archiving or un-validating the underlying framework removes the certification from the public page automatically, with no edit to the certification (RG-TC-08 / RG-TC-09). The global `TrustCenterSettings.is_published` switch is enforced separately at the view layer.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-12 | The percentage is shown only when the per-item `show_percentage` AND the global `show_compliance_percentages` are both on. |
| RG-TC-13 | The percentage is the rounded `Framework.compliance_level`; a missing / non-numeric value yields `None`. |
| RG-TC-02 | The `framework` FK is `PROTECT` : a framework still referenced by a certification cannot be hard-deleted. |
| RG-TC-08 | Dual gate : `published` state AND a reportable-state framework. |

## Endpoints

### REST (management, authenticated, `/api/v1/trust-center/`)

- `GET /certifications/` : list (search on `public_label`, `public_description`; ordering on `display_order`, `public_label`, `created_at`; `?workflow_state=` filter).
- `POST /certifications/`
- `GET /certifications/{id}/`
- `PUT/PATCH /certifications/{id}/`
- `DELETE /certifications/{id}/`
- `POST /certifications/{id}/transition/` : run a publication transition (`target_state`, optional `comment`).

### REST (public, `/trust/api/`)

- `GET /trust/api/certifications/` : published certifications via `PublicCertificationSerializer` (fields: `label`, `description`, `compliance_level` nullable, `logo` sanitized). Also included in the aggregate `GET /trust/api/`.

### MCP

- `list_trust_center_certification` / `get_trust_center_certification` / `create_trust_center_certification` / `update_trust_center_certification` / `delete_trust_center_certification`
- `transition_trust_center_certification` / `trust_center_certification_allowed_transitions`

## Permissions

| Codename | Description |
|---|---|
| `trust_center.certification.read` | List / read certifications |
| `trust_center.certification.create` | Create a certification |
| `trust_center.certification.update` | Modify a certification (and archive a draft / unpublished one) |
| `trust_center.certification.delete` | Hard-delete a certification |
| `trust_center.certification.approve` | Publish / unpublish / archive a published certification |

## References

- `compliance.Framework` (`compliance.models.framework.Framework`) and its `compliance_level` property : [m3-compliance/framework.md](../m3-compliance/framework.md).
- [TrustCenterSettings](trust-center-settings.md) : the global `show_compliance_percentages` toggle.
- [README.md](README.md) : §3 (multi-domain exposure), §6 (data-leakage safety).
