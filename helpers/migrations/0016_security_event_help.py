"""The page of a security event gets its help.

It had none : the register said what an event is, and the page of one event,
where the A.5.25 assessment is written, said nothing of what to do there. The
help is titled with the name of the page and says, in plain words, what an
event is, with examples, and the three ways an assessment ends
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.event_detail": (
        ("Security event",
         "A security event is one report of something someone noticed. A suspicious message, a badge used at night, an alert of the monitoring. Assess it : write what you checked in the assessment notes, then discard it, record it as a weakness, or promote it to an incident."),
        ("Événement de sécurité",
         "Un événement de sécurité est le signalement d'une chose que quelqu'un a remarquée. Un message suspect, un badge utilisé la nuit, une alerte de la supervision. Évaluez-le : notez ce que vous avez vérifié dans les notes d'évaluation, puis écartez-le, enregistrez-le comme faille ou promouvez-le en incident."),
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
        ("helpers", "0015_document_version_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
