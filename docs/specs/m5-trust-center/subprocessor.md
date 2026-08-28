# TrustCenterSubprocessor

`trust_center.models.subprocessor.TrustCenterSubprocessor`

An `assets.Supplier` published on the public Trust Center as a subprocessor (GDPR Art. 28 transparency : the list of third parties that process customer data on the organization's behalf). The entry references the internal supplier through a `PROTECT` foreign key but exposes only curator-chosen public fields; internal supplier data (contacts, contracts, notes, criticality, owner) never reaches the public surface.

File: `trust_center/models/subprocessor.py`

`BaseModel` subclass : UUID PK, sequential `reference` (prefix **`TCSP`**, e.g. `TCSP-1`), `django-simple-history` audit trail, and the `trust_center_publication` lifecycle workflow.

## Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto `TCSP-N`, unique | Business reference |
| `supplier` | relation | FK -> `assets.Supplier`, `PROTECT`, required | The internal supplier surfaced as a subprocessor. `related_name="trust_center_entries"`. |
| `public_name` | string | required, max 255 | Public-facing name of the subprocessor |
| `purpose` | string | optional, max 255, blank default | What the subprocessor is used for (e.g. "Cloud hosting", "Email delivery") |
| `public_country` | string | optional, max 100, blank default | Curator-chosen country (for data-residency transparency). Distinct from any internal supplier country field. |
| `public_website` | url | optional, blank default | Public website of the subprocessor |
| `display_order` | int | `PositiveIntegerField`, default `0` | Render order within the Subprocessors section |
| `workflow_state` | string | indexed | Lifecycle state (`trust_center_publication`) |
| `created_by` | relation | FK -> User | Creator |
| `created_at` / `updated_at` | datetime | auto | Timestamps |
| `tags` | relation | M2M -> Tag | Free tagging (from `BaseModel`) |

`Meta.ordering = ["display_order", "public_name"]`.

## Computed properties

### `workflow_perm_namespace`

Returns `"trust_center.subprocessor"`, so lifecycle transitions resolve their permission against the `subprocessor` feature.

## Lifecycle

Runs the shared `trust_center_publication` workflow (see [README.md §2.3](README.md#23-the-trust_center_publication-workflow)). Publish / unpublish / archive-from-published require `approve`; archiving a draft / unpublished entry is `update`.

## Publish gate (dual gate)

`SubprocessorQuerySet.published()` returns an entry only when **all** of:

1. its `workflow_state` is `published`, AND
2. its `supplier.workflow_state` is in the supplier's reportable states, AND
3. its `supplier.status` is `active`.

So a supplier that is suspended, under evaluation, archived or un-validated drops out of the public list automatically (RG-TC-08 / RG-TC-09 / RG-TC-14). The global `is_published` switch is enforced separately at the view layer.

## Business rules

| ID | Rule |
|---|---|
| RG-TC-14 | A subprocessor is public only when its supplier is reportable AND `status = active`. |
| RG-TC-15 | Only `public_name`, `purpose`, `public_country`, `public_website` and the (sanitized) supplier logo are exposed. Internal supplier fields are never exposed. |
| RG-TC-02 | The `supplier` FK is `PROTECT` : a supplier still referenced by a subprocessor cannot be hard-deleted. |

## Endpoints

### REST (management, authenticated, `/api/v1/trust-center/`)

- `GET /subprocessors/` : list (search on `public_name`, `purpose`, `public_country`; ordering on `display_order`, `public_name`, `created_at`; `?workflow_state=` filter).
- `POST /subprocessors/`
- `GET /subprocessors/{id}/`
- `PUT/PATCH /subprocessors/{id}/`
- `DELETE /subprocessors/{id}/`
- `POST /subprocessors/{id}/transition/`

### REST (public, `/trust/api/`)

- `GET /trust/api/subprocessors/` : published subprocessors via `PublicSubprocessorSerializer` (fields: `name`, `purpose`, `country`, `website`, `logo` sanitized). Also included in the aggregate `GET /trust/api/`.

### MCP

- `list_trust_center_subprocessor` / `get_trust_center_subprocessor` / `create_trust_center_subprocessor` / `update_trust_center_subprocessor` / `delete_trust_center_subprocessor`
- `transition_trust_center_subprocessor` / `trust_center_subprocessor_allowed_transitions`

## Permissions

| Codename | Description |
|---|---|
| `trust_center.subprocessor.read` | List / read subprocessors |
| `trust_center.subprocessor.create` | Create a subprocessor |
| `trust_center.subprocessor.update` | Modify a subprocessor (and archive a draft / unpublished one) |
| `trust_center.subprocessor.delete` | Hard-delete a subprocessor |
| `trust_center.subprocessor.approve` | Publish / unpublish / archive a published subprocessor |

## References

- `assets.Supplier` (`assets.models.supplier.Supplier`) : [m2-assets/supplier.md](../m2-assets/supplier.md). Its `status` and lifecycle state both gate publication.
- [README.md](README.md) : §3 (multi-domain exposure), §6 (data-leakage safety).
