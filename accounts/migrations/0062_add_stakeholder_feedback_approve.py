# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Data migration : add ``context.stakeholder_feedback.approve``.

A stakeholder feedback runs the default lifecycle, whose validation asks for
``approve`` : the feature had no such action, so nobody but a superuser could
validate one. The permission is created and given to the system groups the
``SYSTEM_GROUPS`` rules of ``accounts/constants.py`` select (the
administrators and the RSSI / DPO), as for every other ``approve``.
"""

from django.db import migrations

CODENAME = "context.stakeholder_feedback.approve"
GROUPS = ("Super Administrateur", "Administrateur", "RSSI / DPO")


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")
    perm, _ = Permission.objects.get_or_create(
        codename=CODENAME,
        defaults={
            "name": "Governance - Stakeholder feedback - Approve",
            "module": "context",
            "feature": "stakeholder_feedback",
            "action": "approve",
            "is_system": True,
        },
    )
    for group in Group.objects.filter(name__in=GROUPS, is_system=True):
        group.permissions.add(perm)


def reverse(apps, schema_editor):
    apps.get_model("accounts", "Permission").objects.filter(codename=CODENAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0061_add_controls_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
