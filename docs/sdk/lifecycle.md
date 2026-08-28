# Declaring a lifecycle

Every domain record runs a registered lifecycle. It is the platform's governance
backbone : the step a record sits on decides whether it counts in reports,
whether other objects may link to it, and whether it may be deleted at all.

The canonical contract is
[governance/workflow.md](../specs/governance/workflow.md); the engine internals
are [governance/lifecycle.md](../specs/governance/lifecycle.md); the shipped
lifecycles are listed in
[reference/generated/lifecycles.md](../reference/generated/lifecycles.md).
This page is how you add one.

## Do you need one

No, usually. A model that inherits `BaseModel` and declares no `LIFECYCLE_NAME`
runs the default four-step lifecycle : Draft, Pending validation, Validated,
Archived. That is the right answer for anything whose only governance question
is "has this been approved".

Declare a specific lifecycle when the entity has **operational stages** that
mean something to the business : an incident that is detected, then triaged,
then contained; a contract that is active, then expired.

## The two structures

A **step** carries governance metadata:

| Field | Effect |
| --- | --- |
| `code` | The stored value in `workflow_state` |
| `label` | Shown in the stepper and the badge. Lazy-translated |
| `kind` | `DRAFT` (exactly one, the entry), `INTERMEDIATE`, or `ARCHIVED` (at least one, the exit) |
| `counts_in_reports` | Read by `reportable()` : dashboards, KPIs, reports |
| `linkable` | Read by `linkable()` : the object pickers of other forms |
| `deletable` | Read by `deletable_states()` : whether deletion is offered |
| `tone` | The badge colour |
| `triggers` | Behaviours fired on entering the step, currently a confirmation modal |

A **transition** is a permitted move:

| Field | Effect |
| --- | --- |
| `source` / `target` | Step codes; `source=ANY` means "from any state" |
| `label` | The button text |
| `requires_comment` | Forces a comment, recorded on the event |
| `permission_action` | A permission suffix required to perform it, built against the instance's `workflow_perm_namespace` |
| `allowed_roles` | Restricts it to users holding an ISO 27001 role, scoped to the instance |
| `allowed_users` | A callable `(instance) -> iterable[user]` for dynamic restriction |
| `form_class` | A form collected when performing it; its cleaned data lands on the event |

## Declare it from the constants

The transitions live in `<app>/constants.py` and the lifecycle is **generated**
from them, so the constants stay the single source of truth and the interface,
the API and the MCP layer cannot disagree about what is possible.

```python
# assets/constants.py
ATTESTATION_STATES = [
    # (code, label, counts_in_reports, linkable, deletable, is_initial, is_terminal, tone)
    ("draft",    _("Draft"),    False, False, True,  True,  False, "neutral"),
    ("active",   _("Active"),   True,  True,  False, False, False, "success"),
    ("expired",  _("Expired"),  False, False, False, False, True,  "warning"),
    ("archived", _("Archived"), False, False, False, False, True,  "muted"),
]

ATTESTATION_TRANSITIONS = [
    # (source, target, label, requires_comment, permission_action)
    ("draft",  "active",   _("Activate"), False, "approve"),
    ("active", "expired",  _("Expire"),   False, ""),
    ("active", "archived", _("Archive"),  True,  "approve"),
]
```

Use a **tuple or a list, never a set**, for anything the lifecycle builder
iterates. A set's iteration order varies between processes, which makes the
declared lifecycle differ from one run to the next.

```python
# assets/lifecycles.py
from core.lifecycle import lifecycle_from_state_flags, register_lifecycle

ATTESTATION_LIFECYCLE_NAME = "supplier_attestation"

ATTESTATION_LIFECYCLE = register_lifecycle(
    lifecycle_from_state_flags(
        ATTESTATION_LIFECYCLE_NAME,
        ATTESTATION_STATES,
        ATTESTATION_TRANSITIONS,
        layout="graph",
    )
)
```

```python
# assets/models/supplier_attestation.py
class SupplierAttestation(ScopedModel):
    LIFECYCLE_NAME = "supplier_attestation"
    REFERENCE_PREFIX = "SATT"
```

## Declare both bookends explicitly

`lifecycle_from_state_flags` auto-wires a `draft` entry and an `archived` exit
when you leave them out. The edges it generates carry **no**
`permission_action` and **no** `requires_comment`, and any transition with an
empty `permission_action` is open to anyone who can update the record.

Left generated, a lifecycle therefore exposes an
`archive -> restore -> delete` path out of its deletable draft step. On a sealed
evidence artefact that means an A.5.28 record could be destroyed by anyone
holding update. Declare `draft` and `archived` yourself, with gated edges, as
the incidents module does.

## Register it at startup

```python
# assets/apps.py
class AssetsConfig(AppConfig):
    def ready(self):
        from assets import lifecycles  # noqa: F401
```

Omitting this import fails **silently** : `lifecycle_name_for` falls back to the
default four-step lifecycle with no error, in tests as well as in production.
Assert the binding in a test, the way `incidents/tests/test_lifecycles.py` does:

```python
def test_model_resolves_its_lifecycle():
    assert resolve_lifecycle(SupplierAttestation).name == "supplier_attestation"
```

## Never hardcode a step

This is the rule the whole design exists to serve.

```python
# wrong: the report breaks the day a step is added
qs.filter(workflow_state="validated")

# right: the report follows the lifecycle's own governance
reportable(qs)
```

The same goes for `linkable()` in pickers and `deletable_states()` in deletion
logic. Get this right and adding a step to a lifecycle touches nothing else;
get it wrong and every report is a place the new step is silently missing.

## The interface comes for free

A detail page gets the stepper by adding `LifecycleStepperMixin` to the
DetailView and including the shared template:

```django
{% include "includes/lifecycle_stepper.html" %}
```

It renders done, current, next and future steps, the permission-aware next step,
refusal and rework through clickable earlier pills, the archived off-ramp and
the comment modal for transitions that require one. State badges use
`{% workflow_badge obj %}`.

Never use a plain button or a status select for a transition, and never write
per-page stepper markup. Both reintroduce, on one page, the divergence the
engine exists to prevent.

## Changing an existing lifecycle

Adding a step or a transition is safe : `resolve_layout`-style merging does not
apply here, but nothing hardcodes a step, so the new one is picked up by the
governance helpers automatically.

**Removing or renaming a step is a data migration.** Existing rows hold the old
code in `workflow_state`, and the lifecycle will refuse to resolve them. Migrate
the data in the same change.

Administrators can override a lifecycle from `/config/lifecycles/`, so the
code-declared version is the default rather than the last word. The generated
reference documents the shipped defaults.

## Checklist

- [ ] States and transitions declared in `<app>/constants.py`, in an ordered container
- [ ] `draft` and `archived` declared explicitly, with gated edges
- [ ] Lifecycle registered in `<app>/lifecycles.py`
- [ ] `<app>/apps.py` `ready()` imports it
- [ ] Model declares `LIFECYCLE_NAME`
- [ ] A test asserts the model resolves the lifecycle it declares
- [ ] No code compares `workflow_state` to a literal
- [ ] Detail page uses `LifecycleStepperMixin` and the shared stepper
- [ ] Labels translated into French
- [ ] `generate_docs` re-run and committed
