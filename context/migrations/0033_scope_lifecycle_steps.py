"""Migrate scopes onto the standardised lifecycle (core.lifecycle).

The scope no longer runs the legacy default workflow (draft / pending /
validated / archived); it runs the perimeter governance lifecycle
(Draft -> Definition -> Validation -> In force, with Archived as the exit).
``workflow_state`` now holds one of the new step codes, so every legacy value is
remapped:

- ``draft`` and ``archived`` are valid in both generations and are left as is;
- ``pending`` (awaiting sign-off) -> ``validation``;
- ``validated`` (the authoritative state) -> ``in_force``;
- anything else (defensive) is parked on ``draft``.
"""

from django.db import migrations

# Legacy default-workflow code -> new lifecycle step code.
REMAP = {
    "pending": "validation",
    "validated": "in_force",
}

# Valid step codes of the new scope lifecycle.
NEW_STEPS = {"draft", "definition", "validation", "in_force", "archived"}


def to_lifecycle_steps(apps, schema_editor):
    for model_name in ("Scope", "HistoricalScope"):
        model = apps.get_model("context", model_name)
        for old_code, new_code in REMAP.items():
            model.objects.filter(workflow_state=old_code).update(
                workflow_state=new_code
            )
        # Any remaining value that is not a valid new step (defensive: an
        # unexpected leftover code) is parked on the Draft entry.
        model.objects.exclude(workflow_state__in=list(NEW_STEPS)).update(
            workflow_state="draft"
        )


def back_to_status(apps, schema_editor):
    # The new intermediate steps collapse back onto the closest legacy code.
    reverse = {
        "definition": "draft",
        "validation": "pending",
        "in_force": "validated",
    }
    for model_name in ("Scope", "HistoricalScope"):
        model = apps.get_model("context", model_name)
        for new_code, old_code in reverse.items():
            model.objects.filter(workflow_state=new_code).update(
                workflow_state=old_code
            )


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0032_remove_historicalscope_status_and_more"),
    ]

    operations = [
        migrations.RunPython(to_lifecycle_steps, back_to_status),
    ]
