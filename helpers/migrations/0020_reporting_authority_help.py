"""The page of a reporting authority gets its help.

It had none : the page of one body, where its filing channel and its procedure
are written and the entry is validated, said nothing of what to do there. The
help is titled with the name of the page and says, in plain words, what an
authority is, with an example, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.reporting_authority_detail": (
        ("Reporting authority",
         "A reporting authority is a body you may have to notify of an incident. For example the data protection authority or the national incident response team. Fill in its filing channel and its filing procedure, then validate the entry : only a validated authority is named by a generated obligation."),
        ("Autorité de notification",
         "Une autorité de notification est un organisme que vous pouvez devoir prévenir d'un incident. Par exemple l'autorité de protection des données ou le centre national de réponse aux incidents. Renseignez son canal de dépôt et sa procédure de dépôt, puis validez la fiche : seule une autorité validée est citée par une obligation générée."),
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
        ("helpers", "0019_review_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
