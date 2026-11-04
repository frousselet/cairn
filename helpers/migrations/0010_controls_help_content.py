# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 François Rousselet
"""Help banners of module 8 (controls), in English and French."""

from django.db import migrations

HELP_CONTENT = {
    "controls.control_list": (
        ("Controls register",
         "The security controls the organisation operates : what it actually does to meet its requirements "
         "and treat its risks. Each control has an owner, a lifecycle from proposed to implemented, and an "
         "effectiveness derived from the validated runs of its tests, never declared. Create proposed controls "
         "from a framework's requirements to bootstrap the register."),
        ("Registre des mesures",
         "Les mesures de sécurité que l'organisation applique : ce qu'elle fait réellement pour satisfaire ses "
         "exigences et traiter ses risques. Chaque mesure a un responsable, un cycle de vie de proposée à mise "
         "en œuvre, et une efficacité déduite des exécutions validées de ses tests, jamais déclarée. Créez des "
         "mesures proposées à partir des exigences d'un référentiel pour amorcer le registre."),
    ),
    "controls.control_detail": (
        ("Control details",
         "How the control operates, how it is tested and with what result, which requirements it satisfies, "
         "which risks it treats and where it applies. Its effectiveness follows the latest validated run of each "
         "active test; when a test is overdue the effectiveness is flagged as stale. Declaring it implemented "
         "and retiring it go through the lifecycle."),
        ("Détail de la mesure",
         "Comment la mesure fonctionne, comment elle est testée et avec quel résultat, quelles exigences elle "
         "satisfait, quels risques elle traite et où elle s'applique. Son efficacité suit la dernière exécution "
         "validée de chaque test actif ; quand un test est en retard, l'efficacité est signalée comme ancienne. "
         "La déclaration de mise en œuvre et le retrait passent par le cycle de vie."),
    ),
    "controls.test_list": (
        ("Test register",
         "Every test of every control : who performs it, how often, its latest validated result and when it is "
         "next due. The next due date follows the last validated run and the test's frequency; an overdue test "
         "is shown in red and its tester is reminded."),
        ("Registre des tests",
         "Tous les tests de toutes les mesures : qui les réalise, à quelle fréquence, leur dernier résultat "
         "validé et leur prochaine échéance. L'échéance suit la dernière exécution validée et la fréquence du "
         "test ; un test en retard apparaît en rouge et son testeur est relancé."),
    ),
    "controls.test_detail": (
        ("Test details",
         "What the test establishes, the procedure the tester follows and what a pass looks like. A test can be "
         "activated once its control is planned or implemented and it has a procedure and acceptance criteria. "
         "Record a run each time the test is performed."),
        ("Détail du test",
         "Ce que le test établit, la procédure suivie par le testeur et ce qu'est un succès. Un test peut être "
         "activé dès que sa mesure est planifiée ou mise en œuvre et qu'il a une procédure et des critères "
         "d'acceptation. Enregistrez une exécution à chaque réalisation du test."),
    ),
    "controls.run_detail": (
        ("Run details",
         "Who tested, when, over which period, on which sample, with what result and which evidence. While the "
         "run is in progress its content and evidence can change; once submitted it is frozen, and it is "
         "validated by a reviewer who did not perform it. A validated partial or failed run can raise a finding "
         "in the nonconformity register."),
        ("Détail de l'exécution",
         "Qui a testé, quand, sur quelle période, sur quel échantillon, avec quel résultat et quelles preuves. "
         "Tant que l'exécution est en cours, son contenu et ses preuves peuvent changer ; une fois soumise, elle "
         "est figée, et elle est validée par un relecteur qui ne l'a pas réalisée. Une exécution validée partielle "
         "ou en échec peut ouvrir un constat dans le registre des non-conformités."),
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
        ("helpers", "0009_documents_help_content"),
    ]

    operations = [migrations.RunPython(populate, reverse)]
