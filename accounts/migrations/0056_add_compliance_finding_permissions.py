# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Data migration: add the compliance.finding feature.

Findings used to be gated by ``compliance.assessment.*`` because a finding
could only exist inside an audit. They are now the organisation-wide
nonconformity register, fed by incidents, management reviews, monitoring and
complaints as well, so they get their own feature.

Re-gating an existing surface is a breaking change for anyone already using
it, so this migration does two things rather than one:

1. seeds the six system groups per the ``SYSTEM_GROUPS`` filter rules in
   ``accounts/constants.py``, matching what the test fixture derives from
   the registry;
2. grants ``compliance.finding.<action>`` to **every** group, system or
   custom, that already holds ``compliance.assessment.<action>``.

Step 2 is what makes the upgrade non-breaking : a user, a role or an
external MCP client that could read findings yesterday can still read them
today, without an administrator having to notice and act.
"""

from django.db import migrations

_ACTION_LABELS = {
    "create": "Create",
    "read": "Read",
    "update": "Update",
    "delete": "Delete",
    "validate": "Validate",
}

ACTIONS = ["create", "read", "update", "delete", "validate"]

NEW_PERMISSIONS = [
    {
        "codename": f"compliance.finding.{action}",
        "name": f"Compliance - Nonconformities - {_ACTION_LABELS[action]}",
        "module": "compliance",
        "feature": "finding",
        "action": action,
    }
    for action in ACTIONS
]

_ALL = [p["codename"] for p in NEW_PERMISSIONS]


def _ends(codenames, *suffixes):
    return [c for c in codenames if c.rsplit(".", 1)[1] in suffixes]


GROUP_PERMISSION_MAP = {
    "Super Administrateur": list(_ALL),
    "Administrateur": list(_ALL),
    "RSSI / DPO": _ends(_ALL, "read", "create", "update", "validate"),
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

    # Carry existing access across the re-gating: whoever holds
    # compliance.assessment.<action> keeps the equivalent on findings.
    for action in ACTIONS:
        target = perm_objects.get(f"compliance.finding.{action}")
        if target is None:
            continue
        holders = Group.objects.filter(
            permissions__codename=f"compliance.assessment.{action}"
        )
        for group in holders:
            group.permissions.add(target)


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(codename__in=_ALL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0055_alter_accesslog_event_type"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
