"""Freeze the risk matrix on Risk and ISO27005Risk at evaluation time.

Adds a `criteria_snapshot` JSONField to both models (and their historical
counterparts) and backfills it for existing evaluated records using the
current state of their assessment's RiskCriteria.
"""

from django.db import migrations, models
from django.utils import timezone


HELP_TEXT = (
    "Frozen copy of the risk matrix and criteria metadata at the time "
    "of first evaluation. Used to keep historical scores immutable even "
    "if the underlying criteria are edited later."
)


def _snapshot_for(criteria, captured_at):
    return {
        "criteria_id": str(criteria.pk),
        "criteria_reference": criteria.reference,
        "criteria_name": criteria.name,
        "criteria_version": criteria.version,
        "matrix": dict(criteria.risk_matrix),
        "captured_at": captured_at,
    }


def backfill_snapshots(apps, schema_editor):
    Risk = apps.get_model("risks", "Risk")
    ISO27005Risk = apps.get_model("risks", "ISO27005Risk")
    now = timezone.now().isoformat()

    for risk in Risk.objects.filter(criteria_snapshot__isnull=True).select_related(
        "assessment__risk_criteria"
    ):
        has_score = any([
            risk.initial_risk_level is not None,
            risk.current_risk_level is not None,
            risk.residual_risk_level is not None,
        ])
        if not has_score:
            continue
        criteria = getattr(getattr(risk, "assessment", None), "risk_criteria", None)
        if not criteria or not criteria.risk_matrix:
            continue
        risk.criteria_snapshot = _snapshot_for(criteria, now)
        risk.save(update_fields=["criteria_snapshot"])

    for iso in ISO27005Risk.objects.filter(criteria_snapshot__isnull=True).select_related(
        "assessment__risk_criteria"
    ):
        if iso.risk_level is None:
            continue
        criteria = getattr(getattr(iso, "assessment", None), "risk_criteria", None)
        if not criteria or not criteria.risk_matrix:
            continue
        iso.criteria_snapshot = _snapshot_for(criteria, now)
        iso.save(update_fields=["criteria_snapshot"])


def reverse_backfill(apps, schema_editor):
    Risk = apps.get_model("risks", "Risk")
    ISO27005Risk = apps.get_model("risks", "ISO27005Risk")
    Risk.objects.update(criteria_snapshot=None)
    ISO27005Risk.objects.update(criteria_snapshot=None)


class Migration(migrations.Migration):

    dependencies = [
        ("risks", "0015_historicalrisktreatmentplan_originating_review_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="risk",
            name="criteria_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=HELP_TEXT,
                null=True,
                verbose_name="Criteria snapshot",
            ),
        ),
        migrations.AddField(
            model_name="historicalrisk",
            name="criteria_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=HELP_TEXT,
                null=True,
                verbose_name="Criteria snapshot",
            ),
        ),
        migrations.AddField(
            model_name="iso27005risk",
            name="criteria_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=HELP_TEXT,
                null=True,
                verbose_name="Criteria snapshot",
            ),
        ),
        migrations.AddField(
            model_name="historicaliso27005risk",
            name="criteria_snapshot",
            field=models.JSONField(
                blank=True,
                help_text=HELP_TEXT,
                null=True,
                verbose_name="Criteria snapshot",
            ),
        ),
        migrations.RunPython(backfill_snapshots, reverse_backfill),
    ]
