"""Refresh the MITRE ATT&CK catalogue from a local JSON file.

Usage:
    python manage.py refresh_mitre_attack [path/to/mitre.json]

When no path is given, the bundled `risks/fixtures/mitre_attack_v15.json` is
used. The command is idempotent: existing techniques are updated by
mitre_id, new ones are created, and any technique listed in the JSON with
`is_active = false` is deactivated rather than deleted (so historical
references in AttackTechnique stay intact).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from risks.models import MitreAttackTechnique


DEFAULT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "fixtures" / "mitre_attack_v15.json"
)


class Command(BaseCommand):
    help = "Refresh the MITRE ATT&CK catalogue from a JSON fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=str(DEFAULT_PATH),
            help="Path to the JSON file to import (defaults to the bundled fixture).",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        version = payload.get("version", "15.1")
        entries = payload.get("techniques", [])
        created = updated = 0
        by_mitre_id = {}
        for entry in entries:
            defaults = {
                "name": entry["name"],
                "description": entry.get("description", ""),
                "tactic": entry["tactic"],
                "url": entry.get("url", ""),
                "version": version,
                "is_active": entry.get("is_active", True),
            }
            obj, was_created = MitreAttackTechnique.objects.update_or_create(
                mitre_id=entry["mitre_id"],
                defaults=defaults,
            )
            by_mitre_id[entry["mitre_id"]] = obj
            if was_created:
                created += 1
            else:
                updated += 1

        # Wire parent_technique FKs (second pass)
        for entry in entries:
            parent_id = entry.get("parent_mitre_id")
            if parent_id and parent_id in by_mitre_id:
                child = by_mitre_id[entry["mitre_id"]]
                child.parent_technique = by_mitre_id[parent_id]
                child.save(update_fields=["parent_technique"])

        self.stdout.write(self.style.SUCCESS(
            f"MITRE ATT&CK catalogue refreshed: {created} created, {updated} updated, "
            f"version {version}."
        ))
