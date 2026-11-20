"""The page of a response plan gets its help.

It had none : the register said what a plan is, and the page of one plan,
where the procedure is written and put into force, said nothing of what to do
there. The help is titled with the name of the page and says, in plain words,
what a plan is, with examples, and what to do first
(docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under this key is
left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "incidents.response_plan_detail": (
        ("Response plan",
         "A response plan is the procedure you follow when an incident happens. For example who is called first, what each severity means, what is kept as evidence. Write the procedure first, then submit the plan for validation : once validated, it is the plan in force, and an incident names it as the plan it is handled under."),
        ("Plan de réponse",
         "Un plan de réponse est la procédure que vous suivez quand un incident survient. Par exemple qui est appelé en premier, ce que signifie chaque gravité, ce qui est conservé comme preuve. Rédigez d'abord la procédure, puis soumettez le plan à validation : une fois validé, c'est le plan en vigueur, et un incident le désigne comme le plan selon lequel il est traité."),
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
        ("helpers", "0016_security_event_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
