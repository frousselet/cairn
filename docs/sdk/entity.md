# Adding a domain entity

The full path, from an empty file to a shipped entity. Every other SDK page is a
detail of one of these steps; this is the order to do them in.

The running example is a **supplier attestation** : a document a supplier
provides to evidence its compliance with a framework, with a validity period.

## 0. Write the specification first

`docs/specs/<module>/supplier-attestation.md`, following the conventions of the
files around it : the importable path at the top, a `| Field | Type |
Constraints | Description |` table, the lifecycle, and references back to the
module's business rules.

Doing this first is not ceremony. The field table is where you discover that
"valid until" is required but "valid from" is not, and that the attestation
belongs to the supplier's perimeter rather than to its own. Discovering that in
the specification costs a paragraph; discovering it after the migration costs a
migration.

Add the row to the module's `README.md` entity table.

## 1. The model

`<app>/models/supplier_attestation.py`, re-exported from `models/__init__.py`.

```python
class SupplierAttestation(ScopedModel):
    """A supplier's evidence of compliance with a framework."""

    REFERENCE_PREFIX = "SATT"          # exactly four characters
    LIFECYCLE_NAME = "supplier_attestation"

    supplier = models.ForeignKey("assets.Supplier", on_delete=models.CASCADE,
                                 related_name="attestations",
                                 verbose_name=_("Supplier"))
    framework = models.ForeignKey("compliance.Framework", on_delete=models.PROTECT,
                                  verbose_name=_("Framework"))
    valid_until = models.DateField(_("Valid until"))
    document = models.FileField(_("Document"), upload_to="attestations/", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Supplier attestation")
        verbose_name_plural = _("Supplier attestations")
        ordering = ["-valid_until"]
```

Choose the base deliberately. `ScopedModel` for anything a user's perimeter
should filter; `BaseModel` for a shared catalogue that everyone sees. Both give
a UUID primary key, timestamps, `created_by`, a lifecycle and versioning.

A child entity that has no perimeter of its own inherits its parent's, and the
path has to be **declared** on the viewset. See
[rest-endpoint.md](rest-endpoint.md#3-declare-tenancy-do-not-assume-it) : the
failure mode when you forget is silent.

```bash
python manage.py makemigrations
python manage.py migrate
```

## 2. Constants and lifecycle

States and transitions in `<app>/constants.py`, the lifecycle registered in
`<app>/lifecycles.py`, imported from `apps.py` `ready()`. The whole of
[lifecycle.md](lifecycle.md), including why both bookends must be declared
explicitly.

Skip this step entirely if the default four-step lifecycle fits.

## 3. Permissions

`accounts/constants.py`, in `PERMISSION_REGISTRY`:

```python
"supplier_attestation": {
    "actions": ["create", "read", "update", "delete", "approve"],
    "label": _("Supplier attestations"),
},
```

Then a data migration to create them. The system groups pick them up
automatically, because a group is a filter over codenames rather than a list.
`approve` belongs there only if a transition declares
`permission_action="approve"`.

## 4. The interface

Form, views, URLs, templates.

```
<app>/forms.py                            a ModelForm
<app>/views.py                            List / Detail / Create / Update / Delete
<app>/urls.py                             routes under /<app>/
<app>/templates/<app>/supplier_attestation_list.html
                     supplier_attestation_detail.html
                     supplier_attestation_form.html
```

The mixins carry most of it : `SortableListMixin` for server-side sorting
persisted per user, `ScopeFilterMixin` for tenancy, `CreatedByMixin` on create,
`LifecycleStepperMixin` on the detail view.

The detail page follows the platform's layout convention : a two-column card
layout, main content left and a sticky metadata sidebar right, with collapsible
sections rather than tabs. See [ui-conventions.md](ui-conventions.md).

Add the entry to the navigation (`core/navigation.py`).

## 5. The REST endpoint

Serializer, viewset, router registration. All of
[rest-endpoint.md](rest-endpoint.md).

## 6. The MCP tools

The full CRUD set plus lifecycle and history, built on the generic handlers. All
of [mcp-tool.md](mcp-tool.md).

Steps 5 and 6 are not optional and not "later". A feature that ships without
them ships a platform whose API is a partial view of itself.

## 7. Translations

Every string wrapped, every French entry added to
`locale/fr/LC_MESSAGES/django.po` in the same change. Watch for a `msgid` that
already exists elsewhere : disambiguate with `pgettext_lazy` and a `msgctxt`
rather than adding a duplicate, which fails `compilemessages` and therefore CI.

```bash
python manage.py compilemessages
```

## 8. Seed data

`scripts/seed_demo_data.py`. The demo dataset (Voltara Energy) feeds the
dashboard, the list views and the documentation screenshots, so an entity with
no seed data leaves those surfaces empty and makes the next screenshot pass
look like a regression.

Exercise every field, including the optional ones.

## 9. Tests

`<app>/tests/`, with a factory in `factories.py` and the coverage
[testing.md](../technical/testing.md#what-a-test-for-a-new-feature-has-to-cover)
sets out : permission on all three surfaces, tenancy, lifecycle, contract,
behaviour.

## 10. Regenerate and document

```bash
python manage.py generate_docs
```

The entity now appears in the generated models, permissions, lifecycles,
endpoints and MCP pages. Then update, by hand:

- `docs/specs/<module>/README.md`, the entity table (if not already done at step 0)
- `docs/user-guide/`, if the interface gained a screen
- `README.md`, if the feature list changes
- `CHANGELOG.md`, one line under `## [Unreleased]`

## Order of operations

```
spec ──▶ model ──▶ migration ──▶ lifecycle ──▶ permissions ──▶ migration
                                                                  │
                              ┌───────────────────────────────────┘
                              ▼
                        interface ──▶ REST ──▶ MCP ──▶ i18n ──▶ seed
                                                                  │
                              ┌───────────────────────────────────┘
                              ▼
                          tests ──▶ generate_docs ──▶ user guide ──▶ changelog
```

## Checklist

- [ ] Specification written and linked from the module README
- [ ] Model inherits the right base; reference prefix is four characters
- [ ] Migration generated and applied
- [ ] Lifecycle declared and registered, or the default deliberately kept
- [ ] Permissions registered and migrated
- [ ] List, detail, create, update, delete views, with the stepper on detail
- [ ] Navigation entry added
- [ ] REST endpoint with tenancy declared
- [ ] MCP tools, full set
- [ ] Strings wrapped and translated; `compilemessages` passes
- [ ] Seed data exercises every field
- [ ] Tests cover permission, tenancy, lifecycle and contract
- [ ] `generate_docs` re-run and committed
- [ ] User guide and changelog updated
