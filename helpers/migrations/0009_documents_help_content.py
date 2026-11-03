# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Help banners of module 7 (documents), in English and French."""

from django.db import migrations

HELP_CONTENT = {
    "documents.policy_list": (
        ("Documents register",
         "The governing documents of the ISMS : policies, procedures, standards, charters and plans. "
         "Each document has one version in force at most, a review date derived from it, and an owner "
         "who is reminded before the review falls due."),
        ("Registre des documents",
         "Les documents qui gouvernent le SMSI : politiques, procédures, standards, chartes et plans. "
         "Chaque document a au plus une version en vigueur, une date de revue qui en découle, et un "
         "propriétaire averti avant l'échéance de la revue."),
    ),
    "documents.policy_detail": (
        ("Document details",
         "The version in force, its approval and fingerprint, every earlier version, and the campaigns "
         "that asked people to acknowledge it. A new version starts from the one in force; once submitted "
         "its content is frozen, and putting it in force supersedes the previous one. Record a review "
         "without change when the document is still accurate."),
        ("Détail du document",
         "La version en vigueur, son approbation et son empreinte, les versions précédentes, et les "
         "campagnes de prise de connaissance. Une nouvelle version part de celle en vigueur ; une fois "
         "soumise, son contenu est figé, et sa mise en vigueur remplace la précédente. Déclarez une revue "
         "sans changement quand le document est toujours juste."),
    ),
    "documents.campaign_list": (
        ("Acknowledgement campaigns",
         "Each campaign asks an audience of users, groups and roles to confirm they have read one version "
         "of a document. The audience is fixed at launch; every confirmation is kept as evidence."),
        ("Campagnes de prise de connaissance",
         "Chaque campagne demande à un public d'utilisateurs, de groupes et de rôles de confirmer avoir lu "
         "une version d'un document. Le public est figé au lancement ; chaque confirmation est conservée "
         "comme preuve."),
    ),
    "documents.campaign_detail": (
        ("Campaign details",
         "Who was asked, who confirmed and when, who is still pending. Add newcomers to include people who "
         "joined a group or role after the launch; excuse a person with a reason when they cannot "
         "acknowledge. A campaign closes on its own when its version is superseded."),
        ("Détail de la campagne",
         "Qui a été sollicité, qui a confirmé et quand, qui reste en attente. Ajoutez les nouveaux "
         "arrivants pour inclure les personnes entrées dans un groupe ou un rôle après le lancement ; "
         "dispensez une personne avec un motif quand elle ne peut pas confirmer. Une campagne se clôt "
         "d'elle-même quand sa version est remplacée."),
    ),
    "documents.acknowledge_list": (
        ("To acknowledge",
         "The documents you are asked to read and acknowledge, with their due dates. Open one, read it, "
         "and confirm : your confirmation is recorded with the date and the statement you accepted."),
        ("À confirmer",
         "Les documents que vous devez lire et dont vous devez confirmer la prise de connaissance, avec "
         "leur échéance. Ouvrez-en un, lisez-le et confirmez : votre confirmation est enregistrée avec la "
         "date et la déclaration acceptée."),
    ),
}


def populate(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for key, ((en_title, en_body), (fr_title, fr_body)) in HELP_CONTENT.items():
        HelpContent.objects.update_or_create(key=key, language="en", defaults={"title": en_title, "body": en_body})
        HelpContent.objects.update_or_create(key=key, language="fr", defaults={"title": fr_title, "body": fr_body})


def reverse(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    HelpContent.objects.filter(key__in=list(HELP_CONTENT)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0008_remove_versioning_help_content"),
    ]

    operations = [migrations.RunPython(populate, reverse)]
