"""The page of a post-incident review gets its help.

It had none : the page of the review, where the lessons of an incident are
written and verified, said nothing of what to do there. The help is titled
with the name of the page and says, in plain words, what a review is, with an
example, and what to do first (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.review_detail": (
        ("Post-incident review",
         "A post-incident review draws the lessons of an incident once it is over. For example the root cause of a ransomware attack, the controls that did not hold and the corrective actions that follow. Start the review, fill in the root cause and check for similar incidents : the review cannot be submitted without them."),
        ("Revue post-incident",
         "Une revue post-incident tire les leçons d'un incident une fois celui-ci terminé. Par exemple la cause racine d'une attaque par rançongiciel, les mesures qui n'ont pas tenu et les actions correctives qui suivent. Démarrez la revue, renseignez la cause racine et recherchez les incidents similaires : la revue ne peut pas être soumise sans eux."),
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
        ("helpers", "0018_evidence_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
