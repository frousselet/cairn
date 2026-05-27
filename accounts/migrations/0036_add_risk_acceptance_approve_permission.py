"""
Data migration: add the risks.acceptance.approve permission and assign it
to the system groups that already hold the other approve permissions.
"""

from django.db import migrations


RISK_ACCEPTANCE_APPROVE = (
    "risks.acceptance.approve",
    "Gestion des risques - Acceptations de risque - Approuver",
    "risks",
    "acceptance",
    "approve",
)


GROUPS_GRANTED = ["Super Administrateur", "Administrateur", "RSSI / DPO"]


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    codename, name, module, feature, action = RISK_ACCEPTANCE_APPROVE
    perm, _ = Permission.objects.get_or_create(
        codename=codename,
        defaults={
            "name": name,
            "module": module,
            "feature": feature,
            "action": action,
            "is_system": True,
        },
    )

    for group_name in GROUPS_GRANTED:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.add(perm)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(codename=RISK_ACCEPTANCE_APPROVE[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0035_add_management_review_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
