"""Data migration: add the AI assistant feedback read permission and assign it
to the system / audit-oriented groups."""

from django.db import migrations


NEW_PERMISSIONS = [
    {
        "codename": "system.assistant_feedback.read",
        "name": "System - AI assistant feedback - Read",
        "module": "system",
        "feature": "assistant_feedback",
        "action": "read",
    },
]

# System-scoped data: granted to the same groups that may read the audit trail
# (Super Admin, Admin, RSSI/DPO, Auditeur); not to Contributeur/Lecteur.
GROUP_PERMISSION_MAP = {
    "Super Administrateur": ["system.assistant_feedback.read"],
    "Administrateur": ["system.assistant_feedback.read"],
    "RSSI / DPO": ["system.assistant_feedback.read"],
    "Auditeur": ["system.assistant_feedback.read"],
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
    Permission.objects.filter(codename__in=[p["codename"] for p in NEW_PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_user_email_notifications_notification"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
