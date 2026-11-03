# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Data migration: add the two permission features of module 7 (documents).

Mirrors the assignment the ``SYSTEM_GROUPS`` filter rules produce: Super Admin
and Admin get all 10, RSSI / DPO 8 (no delete), Contributeur 6, Auditeur and
Lecteur 2 each.
"""

from django.db import migrations

_ACTION_LABELS = {"create": "Create", "read": "Read", "update": "Update", "delete": "Delete", "approve": "Approve"}

FEATURES = {
    "policy": ("Documents", ["create", "read", "update", "delete", "approve"]),
    "acknowledgement": ("Acknowledgement campaigns", ["create", "read", "update", "delete", "approve"]),
}

NEW_PERMISSIONS = [
    {
        "codename": f"documents.{feature}.{action}",
        "name": f"Documents - {label} - {_ACTION_LABELS[action]}",
        "module": "documents",
        "feature": feature,
        "action": action,
    }
    for feature, (label, actions) in FEATURES.items()
    for action in actions
]

_ALL = [p["codename"] for p in NEW_PERMISSIONS]


def _ends(codenames, *suffixes):
    return [c for c in codenames if c.rsplit(".", 1)[1] in suffixes]


GROUP_PERMISSION_MAP = {
    "Super Administrateur": list(_ALL),
    "Administrateur": list(_ALL),
    "RSSI / DPO": _ends(_ALL, "read", "create", "update", "approve"),
    "Auditeur": _ends(_ALL, "read"),
    "Contributeur": _ends(_ALL, "read", "create", "update"),
    "Lecteur": _ends(_ALL, "read"),
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")
    perm_objects = {}
    for data in NEW_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=data["codename"],
            defaults={
                "name": data["name"], "module": data["module"], "feature": data["feature"],
                "action": data["action"], "is_system": True,
            },
        )
        perm_objects[data["codename"]] = perm
    for group_name, codenames in GROUP_PERMISSION_MAP.items():
        try:
            group = Group.objects.get(name=group_name, is_system=True)
        except Group.DoesNotExist:
            continue
        group.permissions.add(*[perm_objects[c] for c in codenames if c in perm_objects])


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(codename__in=_ALL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0057_add_incidents_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
