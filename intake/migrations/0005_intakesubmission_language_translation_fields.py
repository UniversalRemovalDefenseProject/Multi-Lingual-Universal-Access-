from django.db import migrations, models
import django.utils.translation


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0004_intakesubmission_countries_traveled_asylum_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='intakesubmission',
            name='language_preference',
            field=models.CharField(
                choices=[
                    ('en', 'English'),
                    ('es', 'Spanish'),
                    ('fr', 'French'),
                    ('ar', 'Arabic'),
                    ('ht', 'Haitian Creole'),
                    ('ru', 'Russian'),
                    ('hi', 'Hindi'),
                    ('pa', 'Punjabi'),
                    ('pt', 'Portuguese'),
                    ('zh-hans', 'Chinese (Simplified)'),
                ],
                default='en',
                help_text=django.utils.translation.gettext_lazy(
                    'Language used while completing the intake form.'
                ),
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='intakesubmission',
            name='fear_of_return_summary_translated',
            field=models.TextField(
                blank=True,
                help_text=django.utils.translation.gettext_lazy(
                    'Staff translation only. The original response is preserved separately.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='intakesubmission',
            name='past_harm_summary_translated',
            field=models.TextField(
                blank=True,
                help_text=django.utils.translation.gettext_lazy(
                    'Staff translation only. The original response is preserved separately.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='intakesubmission',
            name='countries_traveled_asylum_summary_translated',
            field=models.TextField(
                blank=True,
                help_text=django.utils.translation.gettext_lazy(
                    'Staff translation only. The original response is preserved separately.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='intakesubmission',
            name='translated_response_language',
            field=models.CharField(
                blank=True,
                choices=[
                    ('en', 'English'),
                    ('es', 'Spanish'),
                    ('fr', 'French'),
                    ('ar', 'Arabic'),
                    ('ht', 'Haitian Creole'),
                    ('ru', 'Russian'),
                    ('hi', 'Hindi'),
                    ('pa', 'Punjabi'),
                    ('pt', 'Portuguese'),
                    ('zh-hans', 'Chinese (Simplified)'),
                ],
                help_text=django.utils.translation.gettext_lazy(
                    'Language of any staff-entered translated responses.'
                ),
                max_length=10,
            ),
        ),
    ]
