"""Migrate sites onto the standardised lifecycle (core.lifecycle).

The site no longer runs the legacy default workflow (draft / pending /
validated / archived); it runs the operational site lifecycle (Draft ->
Commissioning -> Operational -> Review, with Decommissioned and Archived as the
off-ramps). ``workflow_state`` now holds one of the new step codes, so every
legacy value is remapped:

- ``draft`` and ``archived`` are valid in both generations and are left as is;
- ``pending`` (submitted, not yet in service) -> ``commissioning``;
- ``validated`` (the authoritative, in-service state) -> ``operational``;
- anything else (defensive) is parked on ``draft``.
"""

from django.db import migrations

# Legacy default-workflow code -> new lifecycle step code.
REMAP = {
    "pending": "commissioning",
    "validated": "operational",
}

# Valid step codes of the new site lifecycle.
NEW_STEPS = {
    "draft",
    "commissioning",
    "operational",
    "review",
    "decommissioned",
    "archived",
}


def to_lifecycle_steps(apps, schema_editor):
    for model_name in ("Site", "HistoricalSite"):
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
        "commissioning": "pending",
        "operational": "validated",
        "review": "validated",
        "decommissioned": "archived",
    }
    for model_name in ("Site", "HistoricalSite"):
        model = apps.get_model("context", model_name)
        for new_code, old_code in reverse.items():
            model.objects.filter(workflow_state=new_code).update(
                workflow_state=old_code
            )


class Migration(migrations.Migration):
    dependencies = [
        ("context", "0033_scope_lifecycle_steps"),
    ]

    operations = [
        migrations.RunPython(to_lifecycle_steps, back_to_status),
    ]
