from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0047_companysettings_accent_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dashboard_layout",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Personal dashboard arrangement: ordered list of {id, size, visible} widget entries.",
                verbose_name="Dashboard layout",
            ),
        ),
    ]
