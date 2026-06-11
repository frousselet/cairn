"""Align assessment ``workflow_state`` with its 6-state ``status`` machine.

Same rationale as 0037 for the action plan: the phase 2 backfill mapped
``workflow_state`` from ``is_approved``; now that the compliance assessment
runs its specific ``compliance_assessment`` workflow, the state codes are the
status values themselves. Identity copy, historical rows included.
"""

from django.db import migrations
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    HistoricalComplianceAssessment = apps.get_model(
        "compliance", "HistoricalComplianceAssessment"
    )
    ComplianceAssessment.objects.update(workflow_state=F("status"))
    HistoricalComplianceAssessment.objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    ComplianceAssessment = apps.get_model("compliance", "ComplianceAssessment")
    ComplianceAssessment.objects.filter(is_approved=True).update(workflow_state="validated")
    ComplianceAssessment.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("compliance", "0037_action_plan_workflow_state_from_status"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
