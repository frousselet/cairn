"""Data migration: seed the MITRE ATT&CK catalogue from the bundled fixture.

The fixture lives at risks/fixtures/mitre_attack_v15.json and contains a
curated subset of the Enterprise Matrix v15.1 covering the 14 tactics. The
seed is idempotent: existing rows are updated by mitre_id, new rows are
created. Run `python manage.py refresh_mitre_attack <path>` to refresh from
an updated JSON without replaying this migration.
"""

import json
from pathlib import Path

from django.db import migrations


FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "mitre_attack_v15.json"


def seed(apps, schema_editor):
    MitreAttackTechnique = apps.get_model("risks", "MitreAttackTechnique")
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    version = payload.get("version", "15.1")
    # First pass: create / update parentless techniques so parent FKs resolve.
    by_mitre_id = {}
    for entry in payload.get("techniques", []):
        defaults = {
            "name": entry["name"],
            "description": entry.get("description", ""),
            "tactic": entry["tactic"],
            "url": entry.get("url", ""),
            "version": version,
            "is_active": True,
        }
        obj, _ = MitreAttackTechnique.objects.update_or_create(
            mitre_id=entry["mitre_id"],
            defaults=defaults,
        )
        by_mitre_id[entry["mitre_id"]] = obj

    # Second pass: wire parent_technique FKs for sub-techniques.
    for entry in payload.get("techniques", []):
        parent_id = entry.get("parent_mitre_id")
        if parent_id and parent_id in by_mitre_id:
            child = by_mitre_id[entry["mitre_id"]]
            child.parent_technique = by_mitre_id[parent_id]
            child.save(update_fields=["parent_technique"])


def reverse(apps, schema_editor):
    MitreAttackTechnique = apps.get_model("risks", "MitreAttackTechnique")
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    mitre_ids = [entry["mitre_id"] for entry in payload.get("techniques", [])]
    MitreAttackTechnique.objects.filter(mitre_id__in=mitre_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("risks", "0021_ebios_w4_operational_mitre"),
    ]

    operations = [
        migrations.RunPython(seed, reverse),
    ]
