"""Align asset ``workflow_state`` with the physical ``status`` machines.

Same rationale as compliance 0037 / 0038 and reports 0007: the phase 2
backfill mapped ``workflow_state`` from ``is_approved``; now that essential
and support assets run their specific workflows, the state codes are the
status values themselves. Identity copy, historical rows included.
"""

from django.db import migrations
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    for model_name in (
        "EssentialAsset",
        "HistoricalEssentialAsset",
        "SupportAsset",
        "HistoricalSupportAsset",
    ):
        apps.get_model("assets", model_name).objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    for model_name in ("EssentialAsset", "SupportAsset"):
        model = apps.get_model("assets", model_name)
        model.objects.filter(is_approved=True).update(workflow_state="validated")
        model.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0030_assetgroup_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
