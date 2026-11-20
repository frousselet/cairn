"""The page of an obligation template gets its help.

It had none : the page of one rule, where its citation, its clock and its
trigger conditions are written and the rule is validated, said nothing of what
to do there. The help is titled with the name of the page and says, in plain
words, what a template is, with an example, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.obligation_template_detail": (
        ("Obligation template",
         "An obligation template is a rule saying who must be notified of an incident, and when. For example a personal data breach reported to the data protection authority within 72 hours. Fill in its legal reference, its content requirements and its trigger conditions, then validate it : only a validated template generates obligations."),
        ("Modèle d'obligation",
         "Un modèle d'obligation est une règle qui dit qui doit être prévenu d'un incident, et quand. Par exemple une violation de données personnelles déclarée à l'autorité de protection des données sous 72 heures. Renseignez sa référence juridique, ses exigences de contenu et ses conditions de déclenchement, puis validez-le : seul un modèle validé génère des obligations."),
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
        ("helpers", "0020_reporting_authority_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
