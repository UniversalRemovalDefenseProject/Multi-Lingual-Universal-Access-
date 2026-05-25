from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0003_alter_intakesubmission_date_of_birth_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="intakesubmission",
            name="countries_traveled_asylum_summary",
            field=models.TextField(blank=True),
        ),
    ]
