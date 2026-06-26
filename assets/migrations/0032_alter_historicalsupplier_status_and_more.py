"""Merge the supplier lifecycle with its ``status`` field.

The supplier used to carry two independent state fields: the free ``status``
(active / under_evaluation / suspended / archived) and the generic
``workflow_state`` (draft / pending / validated / archived) that drove the
detail stepper. They are now one and the same: the supplier runs a specific
workflow whose state codes ARE the SupplierStatus values, kept coherent with
``status`` via ``sync_legacy_status`` on save (see ``assets/workflows.py``).

This migration realigns the default (under_evaluation, the lifecycle's initial
state) and backfills ``workflow_state`` from ``status`` so existing rows leave
the stale default-lifecycle codes behind. Identity copy, historical rows
included.
"""

from django.db import migrations, models
from django.db.models import F


def copy_status_to_workflow_state(apps, schema_editor):
    for model_name in ("Supplier", "HistoricalSupplier"):
        apps.get_model("assets", model_name).objects.update(workflow_state=F("status"))


def reverse_to_default_mapping(apps, schema_editor):
    for model_name in ("Supplier",):
        model = apps.get_model("assets", model_name)
        model.objects.filter(is_approved=True).update(workflow_state="validated")
        model.objects.filter(is_approved=False).update(workflow_state="draft")


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0031_asset_workflow_state_from_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsupplier',
            name='status',
            field=models.CharField(choices=[('under_evaluation', 'Under evaluation'), ('active', 'Active'), ('suspended', 'Suspended'), ('archived', 'Archived')], default='under_evaluation', max_length=20, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='status',
            field=models.CharField(choices=[('under_evaluation', 'Under evaluation'), ('active', 'Active'), ('suspended', 'Suspended'), ('archived', 'Archived')], default='under_evaluation', max_length=20, verbose_name='Status'),
        ),
        migrations.RunPython(copy_status_to_workflow_state, reverse_to_default_mapping),
    ]
