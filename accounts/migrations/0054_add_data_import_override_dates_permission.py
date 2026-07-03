"""Data migration: add the bulk-import date-override permission.

``system.data_import.override_dates`` lets a trusted admin preserve original
``created_at`` / ``updated_at`` timestamps when creating records via the MCP
``create_*`` / ``batch_create_*`` tools (mass migration from a legacy system).
Granted only to the two administrator roles by default; the timestamps are
ignored for anyone without it.
"""

from django.db import migrations

NEW_PERMISSIONS = [
    {
        "codename": "system.data_import.override_dates",
        "name": "System - Bulk data import - Override creation/modification dates",
        "module": "system",
        "feature": "data_import",
        "action": "override_dates",
    },
]

_ALL = [p["codename"] for p in NEW_PERMISSIONS]

GROUP_PERMISSION_MAP = {
    "Super Administrateur": list(_ALL),
    "Administrateur": list(_ALL),
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
            group.permissions.add(*[perm_objects[c] for c in codenames if c in perm_objects])
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(codename__in=_ALL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0053_add_certificate_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
