"""The page of a management review decision gets its help.

It had none : the page where a decision of a management review is followed up
until it is in place said nothing of what to do there. The help is titled
with the name of the page and says, in plain words, what a decision is, with
an example, and what to do first (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "reports.decision_detail": (
        ("Management review decision",
         "A management review decision is what top management decides to change after a management review. For example, extending the monitoring to the industrial network after an incident. Assign an owner and a due date, fill in the rationale, then record the implementation evidence once the decision is in place."),
        ("Décision de revue de direction",
         "Une décision de revue de direction est ce que la direction décide de changer à l'issue d'une revue. Par exemple, étendre la supervision au réseau industriel après un incident. Désignez un propriétaire et une date d'échéance, renseignez la justification, puis enregistrez la preuve d'implémentation une fois la décision en place."),
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
        ("helpers", "0024_management_review_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
