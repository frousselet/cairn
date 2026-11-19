"""The page of a document version gets its help.

It had none : a reader who followed *Put a version in force* from the page of
a new document landed on an empty version, and nothing said what a version is
nor what to do with it. The help is titled with the name of the page and says,
in plain words, what a version is, with an example, and the way to put it in
force (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "documents.version_detail": (
        ("Document version",
         "A version is the text of a document at one point in time. Version 1.0 of the access control policy, then 1.1 once a rule changes. Write its text or attach its PDF, say what changed, then submit it for review : once approved, it is put in force and replaces the previous one."),
        ("Version de document",
         "Une version est le texte d'un document à un moment donné. La version 1.0 de la politique de contrôle d'accès, puis la 1.1 quand une règle change. Rédigez son texte ou joignez son PDF, dites ce qui a changé, puis soumettez-la en revue : une fois approuvée, elle est mise en vigueur et remplace la précédente."),
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
        ("helpers", "0014_ebios_workshop_helps"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
