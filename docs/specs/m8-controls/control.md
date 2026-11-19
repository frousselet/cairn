# Control

`controls.models.control.Control`

A security control the organisation operates (in French, *mesure de sécurité*) : a durable practice such as "multi-factor authentication on every remote access" or "quarterly access review of the ERP". It satisfies [requirements](../m3-compliance/requirement.md) of any framework, treats [risks](../m4-risks/risk.md), applies to [support assets](../m2-assets/support-asset.md), contributes to [objectives](../m1-context/objective.md) and is described by [documents](../m7-documents/policy.md). Its effectiveness is derived from its [tests](control-test.md) (RG-CTL-14).

File: `controls/models/control.py`

`ScopedModel` subclass : UUID PK, sequential `reference` (prefix **`CTRL`**, e.g. `CTRL-1`), `scopes` M2M, `tags`, `version`, `created_by`, `django-simple-history` audit trail. `LIFECYCLE_NAME = "control"` (see [README §3.1](README.md#31-control)); its exit step `archived` is labelled *Retired*. `workflow_perm_namespace = "controls.control"`.

## Fields

| Field | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK, auto-generated | Unique identifier |
| `reference` | string | auto-generated `CTRL-N`, unique | Business reference |
| `name` | string | required, max 255 | e.g. `Multi-factor authentication on remote access` |
| `description` | text | optional at creation, asked before `planned` and `implemented` | What the control does and how it operates day to day |
| `theme` | enum | optional, no default (asked by the creation dialog) | ISO/IEC 27002:2022 theme : `organizational`, `people`, `physical`, `technological` |
| `nature` | enum | optional, no default | ISO/IEC 27002:2022 control type : `preventive`, `detective`, `corrective` |
| `automation` | enum | optional, no default | `manual`, `semi_automated`, `automated` |
| `owner` | relation | FK -> User, `SET_NULL`, optional | Accountable for the control operating |
| `implemented_on` | date | optional | Stamped (default today) when the control is declared implemented (RG-CTL-02); editable, never in the future |
| `effectiveness` | enum | not editable, default `not_tested` | Derived (RG-CTL-14) : `effective`, `partially_effective`, `not_effective`, `not_tested` |
| `effectiveness_updated_at` | datetime | optional, not editable | When `effectiveness` last changed |
| `workflow_state` | string | indexed, default `draft` | `control` lifecycle step |
| `tags`, `version`, `created_by`, `created_at`, `updated_at` | | | From `BaseModel` |

### Relations

All declared here, with the reverse accessor `controls` on the target (RG-CTL-04 for the pickers).

| Name | Type | Target | Description |
| --- | --- | --- | --- |
| `requirements` | M2M | `compliance.Requirement` | Requirements this control satisfies, from any framework |
| `risks` | M2M | `risks.Risk` | Risks this control treats |
| `treatment_plans` | M2M | `risks.RiskTreatmentPlan` | Treatment plans that create or reinforce it |
| `pacs_measures` | M2M | `risks.PACSMeasure` | EBIOS RM workshop 5 measures that create or reinforce it |
| `support_assets` | M2M | `assets.SupportAsset` | Where the control applies |
| `objectives` | M2M | `context.Objective` | Security objectives it contributes to |
| `policies` | M2M | `documents.Policy` | Documents that describe it (procedure, standard) |

## Computed properties

- `active_tests` : tests in a reportable step.
- `next_test_due` : the earliest `next_due_date` among active tests.
- `is_test_overdue` : RG-CTL-15.
- `is_effectiveness_stale` : `is_test_overdue` and `effectiveness != not_tested`.
- `recompute_effectiveness()` : RG-CTL-14, idempotent, saves only on change.

## Creation and completeness

A control is created short and completed on its page ([usability standard](../../sdk/usability-standard.md)).

- **Creation** asks, on one screen : the name, the theme (a decision : the select opens on *Choose...* and an answer is required), the owner (whoever creates the control, unless they say otherwise), the scopes (not asked when the reader may file under one scope only) and, optionally, the description.
- **No classification is answered for the reader** : `theme`, `nature` and `automation` have no default. They used to default to technological, preventive and manual, which every control created from a requirement (RG-CTL-05) then carried without anybody having chosen it. An empty one reads *Not set*.
- **The edit form has five sections**, one per card of the page : `identity` (name, theme, nature, automation, owner, implemented on, scopes, tags), `description`, `requirements`, `risks` (risks, treatment plans, PACS measures) and `coverage` (support assets, objectives, documents).
- **Completeness** (`Control.COMPLETENESS`), listed on the page under *To complete* and returned as `completeness` by `GET /api/v1/controls/controls/{id}/` and `get_control` :

| Requirement | Key | Blocking |
| --- | --- | --- |
| The description is filled in | `description` | yes : before `planned` and `implemented`, on every surface |
| The theme, the nature and the automation are chosen | `classification` | no |
| The control has an owner | `owner` | no |
| The control is linked to a requirement or to a risk | `answers` | no |
| An implemented control has a test | `tests` | no (asked of an implemented control only) |

A retired control is a closed record : its page lists nothing to complete and offers no edit.

## Validation

- `implemented_on` cannot be in the future.
- The relation pickers offer `linkable_or_linked()` targets.

## Deletion

Only a `draft` (*Proposed*) control without tests is deletable. Otherwise it is retired (RG-CTL-03).

## References

- ISO/IEC 27001:2022 clause 6.1.3 (risk treatment, SoA), 8.1, 9.1; ISO/IEC 27002:2022 attributes (control type, theme)
- [ControlTest](control-test.md), [README.md](README.md) : RG-CTL-01 to RG-CTL-05, RG-CTL-14 to RG-CTL-20
