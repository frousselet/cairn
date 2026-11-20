"""The page of a personal data qualification gets its help.

It had none : the page where an incident is qualified under the GDPR, its
Art. 33(3) content written and its Art. 34 verdict pronounced, said nothing of
what to do there. The help is titled with the name of the page and says, in
plain words, what the qualification is, with an example, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.breach_detail": (
        ("Personal data qualification",
         "A personal data qualification decides whether an incident is a personal data breach. Under the General Data Protection Regulation (GDPR), a breach may have to be reported to the authority within 72 hours, for example invoices readable by other customers. Fill in the nature, the consequences and the measures, assess the high risk to rights and freedoms, then confirm the breach or rule it out."),
        ("Qualification des données personnelles",
         "Une qualification des données personnelles établit si un incident est une violation de données personnelles. Au sens du règlement général sur la protection des données (RGPD), une violation peut devoir être déclarée à l'autorité sous 72 heures, par exemple des factures lisibles par d'autres clients. Renseignez la nature, les conséquences et les mesures, évaluez le risque élevé pour les droits et libertés, puis confirmez la violation ou écartez-la."),
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
        ("helpers", "0021_obligation_template_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
