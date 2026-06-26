"""Migrate suppliers onto the standardised lifecycle (core.lifecycle).

The supplier no longer runs the status-based workflow (under_evaluation /
active / suspended / archived); it runs the audit-proof supplier-risk lifecycle
(Draft -> Onboarding -> ... -> Audit & assurance, with Archived as the exit).
``workflow_state`` now holds one of the new step codes, so every legacy value is
remapped: archived and a never-started draft are preserved, everything else
(the operational statuses and any leftover default-lifecycle code) lands on
``onboarding``, the entry to the operational cycle.
"""

from django.db import migrations

NEW_STEPS = {
    "draft",
    "onboarding",
    "risk_scoring",
    "contracts",
    "ict_chain",
    "cloud",
    "monitoring",
    "change_management",
    "audit_assurance",
    "archived",
}


def to_lifecycle_steps(apps, schema_editor):
    for model_name in ("Supplier", "HistoricalSupplier"):
        model = apps.get_model("assets", model_name)
        # Any value that is not already a valid new step (the old statuses,
        # 'validated', 'pending', ...) becomes 'onboarding'. 'draft' and
        # 'archived' are valid new steps and are left untouched.
        model.objects.exclude(workflow_state__in=list(NEW_STEPS)).update(
            workflow_state="onboarding"
        )


def back_to_status(apps, schema_editor):
    for model_name in ("Supplier", "HistoricalSupplier"):
        model = apps.get_model("assets", model_name)
        model.objects.exclude(workflow_state__in=["draft", "archived"]).update(
            workflow_state="active"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0032_alter_historicalsupplier_status_and_more"),
    ]

    operations = [
        migrations.RunPython(to_lifecycle_steps, back_to_status),
    ]
