"""
Data migration: add management review permissions (ISO 27001:2022 clause 9.3)
and stakeholder feedback permissions, and assign them to system groups.
"""

from django.db import migrations


MANAGEMENT_REVIEW_PERMISSIONS = [
    # reports.management_review
    ("reports.management_review.create", "Rapports - Revues de direction - Créer", "reports", "management_review", "create"),
    ("reports.management_review.read", "Rapports - Revues de direction - Lire", "reports", "management_review", "read"),
    ("reports.management_review.update", "Rapports - Revues de direction - Modifier", "reports", "management_review", "update"),
    ("reports.management_review.delete", "Rapports - Revues de direction - Supprimer", "reports", "management_review", "delete"),
    ("reports.management_review.approve", "Rapports - Revues de direction - Approuver", "reports", "management_review", "approve"),
    # context.stakeholder_feedback
    ("context.stakeholder_feedback.create", "Gouvernance - Retours des parties intéressées - Créer", "context", "stakeholder_feedback", "create"),
    ("context.stakeholder_feedback.read", "Gouvernance - Retours des parties intéressées - Lire", "context", "stakeholder_feedback", "read"),
    ("context.stakeholder_feedback.update", "Gouvernance - Retours des parties intéressées - Modifier", "context", "stakeholder_feedback", "update"),
    ("context.stakeholder_feedback.delete", "Gouvernance - Retours des parties intéressées - Supprimer", "context", "stakeholder_feedback", "delete"),
]


GROUP_FILTERS = {
    "Super Administrateur": lambda codename: True,
    "Administrateur": lambda codename: True,
    "RSSI / DPO": lambda codename: (
        codename.endswith(".read")
        or codename.endswith(".create")
        or codename.endswith(".update")
        or codename.endswith(".approve")
    ),
    "Auditeur": lambda codename: codename.endswith(".read"),
    "Contributeur": lambda codename: (
        codename.endswith(".read")
        or (codename.startswith("context.stakeholder_feedback.") and (
            codename.endswith(".create") or codename.endswith(".update")
        ))
    ),
    "Lecteur": lambda codename: codename.endswith(".read"),
}


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    all_perms = []
    for codename, name, module, feature, action in MANAGEMENT_REVIEW_PERMISSIONS:
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
        all_perms.append(perm)

    for group_name, filter_fn in GROUP_FILTERS.items():
        try:
            group = Group.objects.get(name=group_name)
            matching = [p for p in all_perms if filter_fn(p.codename)]
            group.permissions.add(*matching)
        except Group.DoesNotExist:
            pass


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [c for c, _, _, _, _ in MANAGEMENT_REVIEW_PERMISSIONS]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0034_add_last_seen_version"),
        ("reports", "0004_alter_historicalreport_report_type_and_more"),
        ("context", "0023_historicalstakeholderfeedback_stakeholderfeedback"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
