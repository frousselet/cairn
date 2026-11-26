"""The register of the agent skills and the page of a skill get their help.

Both pages are new. Each help is titled with the name of the page and says,
in plain words, what an agent skill is, with an example, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under one of
these keys is left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "mcp.skill_list": (
        ("Agent skills",
         "An agent skill is a procedure of your organization, written for the AI assistants connected to Cairn. For example : how you onboard a supplier, or who must approve a risk acceptance. Create a skill, write its instructions on its page, then validate it : only then do the assistants read it. A skill named like one Cairn ships replaces it."),
        ("Compétences d'agent",
         "Une compétence d'agent est une procédure de votre organisation, écrite pour les assistants d'intelligence artificielle connectés à Cairn. Par exemple : la façon dont vous référencez un fournisseur, ou qui doit approuver une acceptation de risque. Créez une compétence, rédigez ses instructions sur sa page, puis validez-la : les assistants ne la lisent qu'ensuite. Une compétence qui porte le nom d'une compétence fournie par Cairn la remplace."),
    ),
    "mcp.skill_detail": (
        ("Agent skill",
         "An agent skill is one procedure the AI assistants follow when they work in Cairn. For example, the steps of your supplier onboarding and the tools to call at each one. Write the instructions, then submit the skill : once validated, the assistants read it as you wrote it."),
        ("Compétence d'agent",
         "Une compétence d'agent est une procédure que les assistants d'intelligence artificielle suivent lorsqu'ils travaillent dans Cairn. Par exemple, les étapes du référencement d'un fournisseur et les outils à appeler à chacune. Rédigez les instructions, puis soumettez la compétence : une fois validée, les assistants la lisent telle que vous l'avez écrite."),
    ),
}


def write_the_help(apps, schema_editor):
    HelpContent = apps.get_model("helpers", "HelpContent")
    for key, texts in HELP.items():
        for language, (title, body) in zip(("en", "fr"), texts):
            if not HelpContent.objects.filter(key=key, language=language).exists():
                HelpContent.objects.create(key=key, language=language, title=title, body=body)


class Migration(migrations.Migration):

    dependencies = [
        ("helpers", "0026_stakeholder_feedback_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
