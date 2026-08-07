from django.db import migrations

GROUP_NAME = 'Case Manager'
PERMISSION_CODENAME = 'access_dashboard'
PERMISSION_NAME = 'Can access the case manager dashboard'


def create_case_manager_group(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    # create_permissions() only runs at post_migrate, so on a fresh database neither
    # row exists yet. get_or_create on the same keys it uses (content_type + codename)
    # means whichever runs first wins and the other finds the existing row.
    content_type, _ = ContentType.objects.get_or_create(
        app_label='intake',
        model='intakesubmission',
    )
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename=PERMISSION_CODENAME,
        defaults={'name': PERMISSION_NAME},
    )
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.add(permission)


def delete_case_manager_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    # The permission itself is owned by the model's Meta, so 0006 reverses it.
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0006_alter_intakesubmission_options'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_case_manager_group, delete_case_manager_group),
    ]
