"""The page of an evidence item gets its help.

It had none : the page of one artefact, where its acquisition is completed,
sealed and kept, said nothing of what to do there. The help is titled with the
name of the page and says, in plain words, what an evidence item is, with
examples, and what to do first (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.evidence_detail": (
        ("Evidence item",
         "An evidence item is one artefact kept to prove what happened during an incident. For example a memory image, a log extract or a seized laptop. Say when, by whom and from where it was collected, then record its content hash and its collection method and seal it : from then on, its acquisition can no longer change."),
        ("Preuve",
         "Une preuve est un artefact conservé pour établir ce qui s'est passé pendant un incident. Par exemple une image mémoire, un extrait de journaux ou un ordinateur saisi. Indiquez quand, par qui et d'où elle a été collectée, puis renseignez son empreinte et sa méthode de collecte et scellez-la : dès lors, son acquisition ne peut plus changer."),
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
        ("helpers", "0017_response_plan_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
