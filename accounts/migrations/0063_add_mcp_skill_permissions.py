# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Data migration : add the ``system.mcp_skill`` feature (agent skills).

Mirrors the assignment the ``SYSTEM_GROUPS`` filter rules of
``accounts/constants.py`` produce : Super Admin and Admin get all 5, RSSI / DPO
4 (no delete), Auditeur the read; Contributeur and Lecteur nothing, as for
every ``system.`` feature.
"""

from django.db import migrations

_ACTION_LABELS = {"create": "Create", "read": "Read", "update": "Update", "delete": "Delete", "approve": "Approve"}
ACTIONS = ["create", "read", "update", "delete", "approve"]
CODENAMES = [f"system.mcp_skill.{action}" for action in ACTIONS]

GROUP_PERMISSION_MAP = {
    "Super Administrateur": list(CODENAMES),
    "Administrateur": list(CODENAMES),
    "RSSI / DPO": [c for c in CODENAMES if not c.endswith(".delete")],
    "Auditeur": [c for c in CODENAMES if c.endswith(".read")],
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")
    perms = {}
    for action in ACTIONS:
        codename = f"system.mcp_skill.{action}"
        perms[codename], _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                "name": f"System - Agent skills - {_ACTION_LABELS[action]}",
                "module": "system",
                "feature": "mcp_skill",
                "action": action,
                "is_system": True,
            },
        )
    for group in Group.objects.filter(name__in=GROUP_PERMISSION_MAP, is_system=True):
        group.permissions.add(*(perms[c] for c in GROUP_PERMISSION_MAP[group.name]))


def reverse(apps, schema_editor):
    apps.get_model("accounts", "Permission").objects.filter(codename__in=CODENAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0062_add_stakeholder_feedback_approve"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
