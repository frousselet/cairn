"""Fold the publication ``status`` of Scope, Site and SwotAnalysis into the lifecycle.

Per the approved mapping (issue #105): ``active`` / ``validated`` become the
``validated`` lifecycle state, ``archived`` becomes ``archived``, and ``draft``
keeps whatever the approval backfill produced. ``is_approved`` follows the
subsumes-approval rule (true iff validated). Runs before the schema migration
that removes the columns.
"""

from django.db import migrations


def fold(apps, schema_editor):
    for model_name in ("Scope", "Site", "SwotAnalysis"):
        model = apps.get_model("context", model_name)
        historical = apps.get_model("context", f"Historical{model_name}")
        for m in (model, historical):
            m.objects.filter(status__in=["active", "validated"]).update(
                workflow_state="validated", is_approved=True,
            )
            m.objects.filter(status="archived").update(
                workflow_state="archived", is_approved=False,
            )


def unfold(apps, schema_editor):
    # Reverse: derive status back from the lifecycle state.
    for model_name in ("Scope", "Site", "SwotAnalysis"):
        model = apps.get_model("context", model_name)
        active_value = "validated" if model_name == "SwotAnalysis" else "active"
        model.objects.filter(workflow_state="validated").update(status=active_value)
        model.objects.filter(workflow_state="archived").update(status="archived")
        model.objects.filter(workflow_state__in=["draft", "pending"]).update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("context", "0030_activity_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(fold, unfold),
    ]
