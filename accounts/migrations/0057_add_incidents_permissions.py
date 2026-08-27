# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Data migration: add the six permission features of module 6 (incidents).

Mirrors the assignment the ``SYSTEM_GROUPS`` filter rules in
``accounts/constants.py`` produce, so a production database matches what the
test fixture derives from the registry. Verified against those filters:
Super Admin and Admin get all 30, RSSI / DPO 24, Contributeur 18, Auditeur and
Lecteur 6 each. No filter lambda needed changing (RG-INC-39).
"""

from django.db import migrations

_ACTION_LABELS = {
    "create": "Create",
    "read": "Read",
    "update": "Update",
    "delete": "Delete",
    "approve": "Approve",
    "validate": "Validate",
}

FEATURES = {
    "incident": ("Security incidents", ["create", "read", "update", "delete", "validate"]),
    "event": ("Security events", ["create", "read", "update", "delete", "validate"]),
    "response_plan": ("Incident response plans", ["create", "read", "update", "delete", "approve"]),
    "evidence": ("Incident evidence", ["create", "read", "update", "delete", "approve"]),
    "notification": ("Incident notifications", ["create", "read", "update", "delete", "approve"]),
    "review": ("Post-incident reviews", ["create", "read", "update", "delete", "validate"]),
}

NEW_PERMISSIONS = [
    {
        "codename": f"incidents.{feature}.{action}",
        "name": f"Incidents - {label} - {_ACTION_LABELS[action]}",
        "module": "incidents",
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
    "RSSI / DPO": _ends(_ALL, "read", "create", "update", "approve", "validate"),
    "Auditeur": _ends(_ALL, "read"),
    "Contributeur": _ends(_ALL, "read", "create", "update"),
    "Lecteur": _ends(_ALL, "read"),
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    perm_objects = {}
    for perm_data in NEW_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=perm_data["codename"],
            defaults={
                "name": perm_data["name"],
                "module": perm_data["module"],
                "feature": perm_data["feature"],
                "action": perm_data["action"],
                "is_system": True,
            },
        )
        perm_objects[perm_data["codename"]] = perm

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
        ("accounts", "0056_add_compliance_finding_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
