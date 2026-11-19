"""The page of each EBIOS RM workshop gets its help.

The six workshop pages had none : a reader opened *Workshop 2 - Risk sources*
on three empty tables named with the words of the method, and nothing said
what a risk source is nor what to do first. Each help is titled with the name
of its page and says, in plain words, what the workshop produces, the notions
it uses with an example of each, and where to start
(docs/sdk/usability-standard.md, rule W4).

Only missing rows are created : a help someone already wrote under one of
these keys is left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "risks.ebios_workshop_0": (
        ("Workshop 0 - Study framework",
         "The study framework says what the study is for and how far it goes. Its mission, the business and technical perimeters, the people who take part, the frameworks that apply and the constraints. Fill it in before the first workshop : every later choice is judged against it."),
        ("Atelier 0 - Cadre de l'étude",
         "Le cadre de l'étude dit à quoi sert l'étude et jusqu'où elle va. Sa mission, les périmètres métier et technique, les personnes qui y participent, les référentiels applicables et les contraintes. Renseignez-le avant le premier atelier : chaque choix ultérieur se juge par rapport à lui."),
    ),
    "risks.ebios_workshop_1": (
        ("Workshop 1 - Security baseline",
         "Workshop 1 says what the study protects and where the organisation stands. Choose the business values (the activities and the essential assets) with the support assets they rely on, then add a feared event for each essential asset : the customer file is disclosed, production stops. Rate its gravity, and note the baseline gaps, the rules of your frameworks that are not met yet."),
        ("Atelier 1 - Socle de sécurité",
         "L'atelier 1 dit ce que l'étude protège et où en est l'organisation. Choisissez les valeurs métier (les activités et les biens essentiels) et les biens supports sur lesquels elles reposent, puis ajoutez un événement redouté pour chaque bien essentiel : le fichier clients est divulgué, la production s'arrête. Évaluez sa gravité, et notez les écarts au socle, les règles de vos référentiels qui ne sont pas encore respectées."),
    ),
    "risks.ebios_workshop_2": (
        ("Workshop 2 - Risk sources",
         "Workshop 2 names who could attack the organisation, and what for. A risk source is an attacker, such as a criminal group, a competitor or a disgruntled employee; a targeted objective is the goal pursued : money, espionage, sabotage. Rate each source, pair each source with its objectives and retain the pairs that matter : the next workshops study those."),
        ("Atelier 2 - Sources de risque",
         "L'atelier 2 nomme qui pourrait attaquer l'organisation, et dans quel but. Une source de risque est un attaquant, par exemple un groupe criminel, un concurrent ou un salarié mécontent ; un objectif visé est le but poursuivi : l'argent, l'espionnage, le sabotage. Évaluez chaque source, associez-la à ses objectifs et retenez les couples qui comptent : les ateliers suivants les étudient."),
    ),
    "risks.ebios_workshop_3": (
        ("Workshop 3 - Strategic scenarios",
         "Workshop 3 describes how a risk source would reach its objective through your ecosystem. An ecosystem stakeholder is a supplier, a partner or a client an attack can come through : rate how much you depend on each one and how far you trust it. Then write the strategic scenarios, the attack paths from a retained pair to a feared event, and rate their gravity."),
        ("Atelier 3 - Scénarios stratégiques",
         "L'atelier 3 décrit comment une source de risque atteindrait son objectif en passant par votre écosystème. Une partie prenante de l'écosystème est un fournisseur, un partenaire ou un client par lequel une attaque peut passer : évaluez votre dépendance envers chacune et la confiance que vous lui accordez. Écrivez ensuite les scénarios stratégiques, les chemins d'attaque d'un couple retenu jusqu'à un événement redouté, et évaluez leur gravité."),
    ),
    "risks.ebios_workshop_4": (
        ("Workshop 4 - Operational scenarios",
         "Workshop 4 turns each strategic scenario into the steps an attacker would really take. An operational scenario lists these steps on your support assets, from the first intrusion to the damage, with the attack techniques used. Rate its likelihood, from minimal to maximal : with the gravity, it gives the level of the risk, which you can then add to the risk register."),
        ("Atelier 4 - Scénarios opérationnels",
         "L'atelier 4 détaille chaque scénario stratégique en étapes qu'un attaquant suivrait réellement. Un scénario opérationnel liste ces étapes sur vos biens supports, de la première intrusion jusqu'au dommage, avec les techniques d'attaque employées. Évaluez sa vraisemblance, de minimale à maximale : avec la gravité, elle donne le niveau du risque, que vous pouvez ensuite ajouter au registre des risques."),
    ),
    "risks.ebios_workshop_5": (
        ("Workshop 5 - Risk treatment",
         "Workshop 5 decides what is done about the risks the study found. The summary records the strategy for the residual risks and how they are monitored; the security measures, each with an owner and a target date, make the continuous security improvement plan (PACS). Add the measures, then submit the workshop for review."),
        ("Atelier 5 - Traitement du risque",
         "L'atelier 5 décide de ce qui est fait des risques que l'étude a relevés. La synthèse consigne la stratégie retenue pour les risques résiduels et la façon de les surveiller ; les mesures de sécurité, chacune avec un propriétaire et une date cible, forment le plan d'amélioration continue de la sécurité (PACS). Ajoutez les mesures, puis soumettez l'atelier en revue."),
    ),
}


def write_the_helps(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for key, texts in HELP.items():
        for language, (title, body) in zip(("en", "fr"), texts):
            if not HelpContent.objects.filter(key=key, language=language).exists():
                HelpContent.objects.create(key=key, language=language, title=title, body=body)


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0013_help_titles_name_the_thing"),
    ]

    operations = [
        migrations.RunPython(write_the_helps, migrations.RunPython.noop),
    ]
