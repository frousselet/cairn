"""Align action plan ``workflow_state`` with the 8-state ``status`` machine.

The phase 2 backfill mapped ``workflow_state`` from ``is_approved`` (default
lifecycle values); now that the action plan runs its specific ``action_plan``
workflow, the state codes are the status values themselves. Identity copy,
historical rows included.
"""

from django.db import migrations
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    ComplianceActionPlan = apps.get_model("compliance", "ComplianceActionPlan")
    HistoricalComplianceActionPlan = apps.get_model(
        "compliance", "HistoricalComplianceActionPlan"
    )
    ComplianceActionPlan.objects.update(workflow_state=F("status"))
    HistoricalComplianceActionPlan.objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    # Going back to the default lifecycle: approved plans were 'validated',
    # everything else 'draft' (the phase 2 backfill rule).
    ComplianceActionPlan = apps.get_model("compliance", "ComplianceActionPlan")
    ComplianceActionPlan.objects.filter(is_approved=True).update(workflow_state="validated")
    ComplianceActionPlan.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0036_complianceactionplan_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
