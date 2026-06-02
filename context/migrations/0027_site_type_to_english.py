# Generated manually on 2026-06-02

"""Rename Site.type values from French to English (closes #31).

The Site entity was the last place on the platform still using French
TextChoices values (siege, bureau, usine, entrepot, site_distant, autre).
All other modules consistently use English technical values and rely on
the i18n layer for display. The QA report (#31) flagged this as the only
remaining naming inconsistency and asked for alignment.

datacenter is unchanged (was already English).

The rename touches both the live row and the simple-history audit trail,
which mirrors the choices on every historical row.
"""

from django.db import migrations, models


RENAMES = [
    ("siege", "headquarters"),
    ("bureau", "office"),
    ("usine", "factory"),
    ("entrepot", "warehouse"),
    ("site_distant", "remote"),
    ("autre", "other"),
]


def forward(apps, schema_editor):
    Site = apps.get_model("context", "Site")
    Historical = apps.get_model("context", "HistoricalSite")
    for old, new in RENAMES:
        Site.objects.filter(type=old).update(type=new)
        Historical.objects.filter(type=old).update(type=new)


def backward(apps, schema_editor):
    Site = apps.get_model("context", "Site")
    Historical = apps.get_model("context", "HistoricalSite")
    for old, new in RENAMES:
        Site.objects.filter(type=new).update(type=old)
        Historical.objects.filter(type=new).update(type=old)


SITE_CHOICES = [
    ("headquarters", "Headquarters"),
    ("office", "Office"),
    ("factory", "Factory"),
    ("warehouse", "Warehouse"),
    ("datacenter", "Datacenter"),
    ("remote", "Remote site"),
    ("other", "Other"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("context", "0026_indicator_owner_and_links"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
        # Update the field's choices metadata so makemigrations stays clean.
        migrations.AlterField(
            model_name="site",
            name="type",
            field=models.CharField(
                choices=SITE_CHOICES,
                default="other",
                max_length=20,
                verbose_name="Type",
            ),
        ),
        migrations.AlterField(
            model_name="historicalsite",
            name="type",
            field=models.CharField(
                choices=SITE_CHOICES,
                default="other",
                max_length=20,
                verbose_name="Type",
            ),
        ),
    ]
