"""Help banners of the scope and essential-asset pages, in plain words.

The four banners were written for a reader who already knew the subject
("ISO Harmonized Structure §4.3", "CIA criteria"), and the scope one still
said that a single scope could be active at a time, a rule removed with the
scope hierarchy. They now say what the thing is and what the page is for
(docs/sdk/usability-standard.md).

A banner an administrator rewrote is left alone : a row is replaced only
while it still holds the text a previous migration shipped.
"""

from django.db import migrations

# (key, language) -> (shipped title, shipped body, new title, new body)
REWRITES = {
    ("context.scope_list", "en"): (
        "Scopes",
        "The scope defines the boundaries of the management system (ISO Harmonized Structure §4.3). It specifies the organisational, geographical and technical perimeters covered, as well as justified exclusions. Only one scope can be active at a time; previous versions are automatically archived.",
        "Scopes",
        "A scope says what your security work covers : the whole company, one site or one activity. Every other record (assets, risks, frameworks) is filed under a scope, and each user sees the records of the scopes they are given. A scope can contain sub-scopes. ISO 27001 calls this the scope of the management system (clause 4.3).",
    ),
    ("context.scope_list", "fr"): (
        "Périmètres (Scope)",
        "Le périmètre définit le domaine d'application du système de management (structure harmonisée ISO §4.3). Il précise les limites organisationnelles, géographiques et techniques couvertes, ainsi que les exclusions justifiées. Un seul périmètre peut être actif à un instant donné ; les versions précédentes sont automatiquement archivées.",
        "Périmètres",
        "Un périmètre dit ce que couvre votre démarche de sécurité : toute l'entreprise, un site ou une activité. Toutes les autres fiches (biens, risques, référentiels) se rangent sous un périmètre, et chaque utilisateur voit les fiches des périmètres qui lui sont attribués. Un périmètre peut contenir des sous-périmètres. L'ISO 27001 parle du domaine d'application du système de management (article 4.3).",
    ),
    ("context.scope_detail", "en"): (
        "Scope details",
        "This page presents all information about the selected scope: description, geographical and organisational boundaries, exclusions, approval status and version history. You can edit the scope or go back to the list from the action buttons.",
        "Completing a scope",
        "A scope is created with its name, then completed here. The list at the top of the page says what it still needs, and each card has its own Edit button. Before it can be submitted for validation, a scope must say where it stops and name at least one manager.",
    ),
    ("context.scope_detail", "fr"): (
        "Détail du périmètre",
        "Cette page présente l'ensemble des informations du périmètre sélectionné : description, limites géographiques et organisationnelles, exclusions, statut d'approbation et historique des versions. Vous pouvez modifier le périmètre ou revenir à la liste depuis les boutons d'action.",
        "Compléter un périmètre",
        "Un périmètre se crée avec son nom, puis se complète ici. La liste en haut de page indique ce qui lui manque, et chaque carte a son propre bouton Modifier. Avant d'être soumis à validation, un périmètre doit indiquer où il s'arrête et désigner au moins un responsable.",
    ),
    ("assets.essential_asset_list", "en"): (
        "Essential assets",
        "Essential assets are the business processes and information that hold value for the organisation and require protection. Each essential asset is assessed against CIA criteria (Confidentiality, Integrity, Availability) on a scale from 0 to 4. These levels are propagated to associated support assets through dependency relationships.",
        "Essential assets",
        "An essential asset is what the business cannot do without : an information it holds (the customer file) or an activity it runs (payroll). For each one you say how much harm it would do if it were disclosed, wrong or out of reach. These security needs carry over to the systems the asset relies on, its support assets.",
    ),
    ("assets.essential_asset_list", "fr"): (
        "Biens essentiels",
        "Les biens essentiels sont les processus métier et informations qui ont de la valeur pour l'organisme et qui nécessitent une protection. Chaque bien essentiel est évalué selon les critères DIC (Disponibilité, Intégrité, Confidentialité) sur une échelle de 0 à 4. Ces niveaux sont propagés aux biens supports associés via les relations de dépendance.",
        "Biens essentiels",
        "Un bien essentiel est ce dont l'activité ne peut pas se passer : une information qu'elle détient (le fichier clients) ou une activité qu'elle mène (la paie). Pour chacun, vous indiquez la gravité des conséquences s'il était divulgué, faux ou inaccessible. Ces besoins de sécurité se reportent sur les systèmes dont le bien dépend, ses biens supports.",
    ),
    ("assets.essential_asset_detail", "en"): (
        "Essential asset details",
        "This page presents the selected essential asset with its CIA valuation (Confidentiality, Integrity, Availability), classification and linked support assets through dependency relationships.",
        "Completing an essential asset",
        "An essential asset is created with its name and who answers for it, then completed here. The list at the top of the page says what it still needs, and each card has its own Edit button. Its security needs (confidentiality, integrity, availability) must be assessed before it can become active.",
    ),
    ("assets.essential_asset_detail", "fr"): (
        "Détail du bien essentiel",
        "Cette page présente le bien essentiel sélectionné avec sa valorisation DIC (Disponibilité, Intégrité, Confidentialité), sa classification et les biens supports associés via les relations de dépendance.",
        "Compléter un bien essentiel",
        "Un bien essentiel se crée avec son nom et son propriétaire, puis se complète ici. La liste en haut de page indique ce qui lui manque, et chaque carte a son propre bouton Modifier. Ses besoins de sécurité (confidentialité, intégrité, disponibilité) doivent être évalués avant qu'il puisse devenir actif.",
    ),
}


def _swap(apps, source, target):
    """Replace the rows still holding ``source`` by ``target`` (title, body)."""
    HelpContent = apps.get_model("helpers", "HelpContent")
    for (key, language), texts in REWRITES.items():
        old_title, old_body = texts[source], texts[source + 1]
        new_title, new_body = texts[target], texts[target + 1]
        HelpContent.objects.filter(
            key=key, language=language, title=old_title, body=old_body,
        ).update(title=new_title, body=new_body)


def plain_words(apps, schema_editor):
    _swap(apps, 0, 2)


def previous_words(apps, schema_editor):
    _swap(apps, 2, 0)


class Migration(migrations.Migration):
    dependencies = [
        ("helpers", "0010_controls_help_content"),
    ]

    operations = [
        migrations.RunPython(plain_words, previous_words),
    ]
