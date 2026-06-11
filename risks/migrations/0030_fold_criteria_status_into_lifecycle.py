"""Fold the publication ``status`` of RiskCriteria into the lifecycle.

Same mapping as context 0031: active becomes validated, archived stays
archived, draft keeps the approval backfill. Runs before the schema migration
that removes the column.
"""

from django.db import migrations


def fold(apps, schema_editor):
    for model_name in ("RiskCriteria", "HistoricalRiskCriteria"):
        model = apps.get_model("risks", model_name)
        model.objects.filter(status="active").update(
            workflow_state="validated", is_approved=True,
        )
        model.objects.filter(status="archived").update(
            workflow_state="archived", is_approved=False,
        )


def unfold(apps, schema_editor):
    model = apps.get_model("risks", "RiskCriteria")
    model.objects.filter(workflow_state="validated").update(status="active")
    model.objects.filter(workflow_state="archived").update(status="archived")
    model.objects.filter(workflow_state__in=["draft", "pending"]).update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("risks", "0029_risk_assessment_workflow_state_from_status"),
    ]

    operations = [
        migrations.RunPython(fold, unfold),
    ]
