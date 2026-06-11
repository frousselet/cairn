"""Align management review ``workflow_state`` with its 5-state ``status`` machine.

Same rationale as compliance 0037 / 0038: the phase 2 backfill mapped
``workflow_state`` from ``is_approved``; now that the management review runs
its specific ``management_review`` workflow, the state codes are the status
values themselves. Identity copy, historical rows included.
"""

from django.db import migrations
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    ManagementReview = apps.get_model("reports", "ManagementReview")
    HistoricalManagementReview = apps.get_model("reports", "HistoricalManagementReview")
    ManagementReview.objects.update(workflow_state=F("status"))
    HistoricalManagementReview.objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    ManagementReview = apps.get_model("reports", "ManagementReview")
    ManagementReview.objects.filter(is_approved=True).update(workflow_state="validated")
    ManagementReview.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0006_historicalmanagementreview_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
