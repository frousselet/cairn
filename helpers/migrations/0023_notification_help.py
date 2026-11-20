"""The page of a notification obligation gets its help.

It had none : the page where an obligation owed after an incident is decided,
drafted and filed against its legal clock said nothing of what to do there.
The help is titled with the name of the page and says, in plain words, what an
obligation is, with an example, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.notification_detail": (
        ("Notification obligation",
         "A notification obligation is a filing owed to an authority or another recipient after an incident. For example, the General Data Protection Regulation (GDPR) asks for a notification to the authority within 72 hours of awareness. Decide whether it applies, then fill in the channel and the content, and record the filing before the due date."),
        ("Obligation de notification",
         "Une obligation de notification est un dépôt dû à une autorité ou à un destinataire après un incident. Par exemple, le règlement général sur la protection des données (RGPD) impose une notification à l'autorité dans les 72 heures suivant la prise de connaissance. Décidez si elle s'applique, puis renseignez le canal et le contenu, et enregistrez le dépôt avant l'échéance."),
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
        ("helpers", "0022_breach_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
