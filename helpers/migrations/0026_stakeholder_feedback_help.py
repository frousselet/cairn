"""The register of stakeholder feedback and the page of a feedback get their help.

Both pages are new : stakeholder feedback had no page in the interface (the
REST API and the MCP server alone recorded it). Each help is titled with the
name of the page and says, in plain words, what a feedback is, with an
example, and what to do first (docs/sdk/usability-standard.md, rule W4).

Only a missing row is created : a help someone already wrote under one of
these keys is left as it is. Reversing leaves the rows where they are.
"""

from django.db import migrations

# key -> ((English title, English text), (French title, French text))
HELP = {
    "context.feedback_list": (
        ("Stakeholder feedback",
         "Stakeholder feedback is what a stakeholder tells you about your security. For example, a client complains that it was told of a planned outage too late. Record each feedback when you receive it, then assess it and say how you handled it : the management review looks at them."),
        ("Retours des parties intéressées",
         "Les retours des parties intéressées sont ce qu'une partie intéressée vous dit de votre sécurité. Par exemple, un client se plaint d'avoir été prévenu trop tard d'une coupure planifiée. Enregistrez chaque retour dès sa réception, puis évaluez-le et dites comment vous l'avez pris en charge : la revue de direction les examine."),
    ),
    "context.feedback_detail": (
        ("Stakeholder feedback",
         "A stakeholder feedback is one message a stakeholder sent you about your security. For example, an answer to the yearly client survey. Assess its severity, then write what you did about it and set its handling status once it is addressed."),
        ("Retour d'une partie intéressée",
         "Un retour d'une partie intéressée est un message qu'elle vous a adressé sur votre sécurité. Par exemple, une réponse à l'enquête annuelle auprès des clients. Évaluez sa sévérité, puis écrivez ce que vous en avez fait et indiquez où en est sa prise en charge."),
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
        ("helpers", "0025_decision_help"),
    ]

    operations = [
        migrations.RunPython(write_the_help, migrations.RunPython.noop),
    ]
