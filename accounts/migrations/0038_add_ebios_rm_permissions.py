"""
Data migration: register the EBIOS RM (ANSSI v1.5) permissions for the
risks module and grant them to the system groups consistently with the
existing risk module split. Covers workshops W0-W5 in a single shot so
implementation lots W2-W5 do not require schema-level changes for RBAC.
"""

from django.db import migrations


EBIOS_FEATURES = [
    ("ebios_assessment", "EBIOS RM - Pilotage de l'appreciation",
     ["read", "update", "validate"]),
    ("ebios_baseline", "EBIOS RM - Socle de securite (atelier 1)",
     ["create", "read", "update", "delete", "approve"]),
    ("ebios_risk_source", "EBIOS RM - Sources de risque et objectifs (atelier 2)",
     ["create", "read", "update", "delete", "approve"]),
    ("ebios_ecosystem", "EBIOS RM - Parties prenantes ecosysteme (atelier 3)",
     ["create", "read", "update", "delete", "approve"]),
    ("ebios_strategic", "EBIOS RM - Scenarios strategiques (atelier 3)",
     ["create", "read", "update", "delete", "approve"]),
    ("ebios_operational", "EBIOS RM - Scenarios operationnels (atelier 4)",
     ["create", "read", "update", "delete", "approve"]),
    ("ebios_summary", "EBIOS RM - Synthese et PACS (atelier 5)",
     ["create", "read", "update", "delete", "approve"]),
]


ACTION_LABELS = {
    "create": "Creer",
    "read": "Lire",
    "update": "Modifier",
    "delete": "Supprimer",
    "approve": "Approuver",
    "validate": "Valider",
}


def _build_permissions():
    out = []
    for feature, feature_label, actions in EBIOS_FEATURES:
        for action in actions:
            codename = f"risks.{feature}.{action}"
            name = f"Gestion des risques - {feature_label} - {ACTION_LABELS[action]}"
            out.append((codename, name, "risks", feature, action))
    return out


def _grants_for(group_name):
    """Return the subset of the new codenames a system group receives."""
    perms = _build_permissions()
    if group_name in ("Super Administrateur", "Administrateur"):
        return [p[0] for p in perms]
    if group_name == "RSSI / DPO":
        return [
            p[0] for p in perms
            if p[4] in ("read", "create", "update", "approve", "validate")
        ]
    if group_name in ("Auditeur", "Lecteur"):
        return [p[0] for p in perms if p[4] == "read"]
    if group_name == "Contributeur":
        return [p[0] for p in perms if p[4] in ("read", "create", "update")]
    return []


def populate(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Group = apps.get_model("accounts", "Group")

    code_to_perm = {}
    for codename, name, module, feature, action in _build_permissions():
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
        code_to_perm[codename] = perm

    for group_name in (
        "Super Administrateur",
        "Administrateur",
        "RSSI / DPO",
        "Auditeur",
        "Contributeur",
        "Lecteur",
    ):
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        grants = _grants_for(group_name)
        group.permissions.add(*[code_to_perm[c] for c in grants if c in code_to_perm])


def reverse(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    codenames = [p[0] for p in _build_permissions()]
    Permission.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0037_add_risks_extended_approve_permissions"),
    ]

    operations = [
        migrations.RunPython(populate, reverse),
    ]
