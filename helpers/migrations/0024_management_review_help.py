"""The page of a management review gets its help.

It had none : the page where a management review is prepared, held and closed
said nothing of what to do there. The help is titled with the name of the
page and says, in plain words, what a review is, with an example, and what to
do first (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "reports.management_review_detail": (
        ("Management review",
         "A management review gathers top management to assess information security and decide what to change. For example, the annual review goes through the incidents, the audit findings and the objectives of the year. Fill in the agenda and list the participants, then record the decisions, each with an owner and a due date, before closing the review."),
        ("Revue de direction",
         "Une revue de direction réunit la direction pour évaluer la sécurité de l'information et décider des changements. Par exemple, la revue annuelle passe en revue les incidents, les constats d'audit et les objectifs de l'année. Renseignez l'ordre du jour et listez les participants, puis enregistrez les décisions, chacune avec un propriétaire et une échéance, avant de clore la revue."),
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
        ("helpers", "0023_notification_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
