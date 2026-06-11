"""Align risk-process ``workflow_state`` with the legacy ``status`` machines.

Same rationale as the other phase 6 migrations: the phase 2 backfill mapped
``workflow_state`` from ``is_approved``; now that the risk, treatment plan,
acceptance and vulnerability run their specific workflows, the state codes are
the status values themselves. Identity copy, historical rows included.
"""

from django.db import migrations
from django.db.models import F

MODELS = [
    "Risk",
    "HistoricalRisk",
    "RiskTreatmentPlan",
    "HistoricalRiskTreatmentPlan",
    "RiskAcceptance",
    "HistoricalRiskAcceptance",
    "Vulnerability",
    "HistoricalVulnerability",
]


def copy_status_to_workflow_state(apps, schema_editor):
    for model_name in MODELS:
        apps.get_model("risks", model_name).objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    for model_name in ("Risk", "RiskTreatmentPlan", "RiskAcceptance", "Vulnerability"):
        model = apps.get_model("risks", model_name)
        model.objects.filter(is_approved=True).update(workflow_state="validated")
        model.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0026_attackpathstep_workflow_state_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
