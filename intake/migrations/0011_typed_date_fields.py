"""Convert date_of_birth and next_hearing_date from free text to real DateFields.

Three phases: widen the text columns to accept NULL, normalize every value to an ISO
string (or NULL when it cannot be parsed), then cast to date.

Unparseable values are reported to migrate stdout by pk and field name only -- never the
value itself, since date_of_birth is PII and migration output lands in deploy logs. The
recovery path for those rows is the pre-deploy database backup.

Practically irreversible: migration 0003 left these columns NOT NULL, so reversing with
NULL dates present would fail. Reverse is a no-op for the data phase only.
"""

from django.db import migrations, models

from intake.dates import parse_date_string

DATE_FIELDS = ('date_of_birth', 'next_hearing_date')


def normalize_dates(apps, schema_editor):
    IntakeSubmission = apps.get_model('intake', 'IntakeSubmission')
    for row in IntakeSubmission.objects.all().iterator():
        updates = []
        for field in DATE_FIELDS:
            raw = getattr(row, field)
            if not (raw or '').strip():
                setattr(row, field, None)
                updates.append(field)
                continue
            parsed = parse_date_string(raw)
            if parsed is None:
                # pk + field only: no PII in logs. Raw value recoverable from backup.
                print(f'intake.0011: pk={row.pk} {field} unparseable, set to NULL')
            setattr(row, field, parsed.isoformat() if parsed else None)
            updates.append(field)
        if updates:
            row.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ('intake', '0010_case_manager_status_permission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intakesubmission',
            name='date_of_birth',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='intakesubmission',
            name='next_hearing_date',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RunPython(normalize_dates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='intakesubmission',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='intakesubmission',
            name='next_hearing_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
