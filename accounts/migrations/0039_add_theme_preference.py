from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_add_ebios_rm_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='theme_preference',
            field=models.CharField(
                choices=[('system', 'System'), ('light', 'Light'), ('dark', 'Dark')],
                default='system',
                help_text='Light, Dark, or System (follows the OS preference).',
                max_length=10,
                verbose_name='Display theme',
            ),
        ),
    ]
