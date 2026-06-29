"""Data migration: add Certificate permissions and assign them to system groups.

Mirrors the assignment produced by the ``SYSTEM_GROUPS`` filter rules in
``accounts/constants.py`` so the production seed matches what the test fixture
(``conftest.py``) derives from the registry:
- Super Admin / Admin: all permissions
- RSSI / DPO: read, create, update, approve (no delete)
- Contributeur: read, create, update (no approve, no delete)
- Auditeur / Lecteur: read only
"""

from django.db import migrations

_ACTION_LABELS = {
    "create": "Create",
    "read": "Read",
    "update": "Update",
    "delete": "Delete",
    "approve": "Approve",
}

NEW_PERMISSIONS = [
    {
        "codename": f"assets.certificate.{action}",
        "name": f"Assets - Certificates - {_ACTION_LABELS[action]}",
        "module": "assets",
        "feature": "certificate",
        "action": action,
    }
    for action in ["create", "read", "update", "delete", "approve"]
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
            perms_to_add = [perm_objects[c] for c in codenames if c in perm_objects]
            group.permissions.add(*perms_to_add)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [p["codename"] for p in NEW_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0052_add_contract_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
