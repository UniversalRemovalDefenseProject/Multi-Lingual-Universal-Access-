from django.db import migrations

GROUP_NAME = 'Case Manager'
PERMISSION_CODENAME = 'change_case_status'
PERMISSION_NAME = 'Can change case status'


def grant_status_permission(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    # Same shape as 0007: create_permissions() only runs at post_migrate, so on a fresh
    # database neither row exists yet. get_or_create on the keys create_permissions uses
    # (content_type + codename) means whichever runs first wins and the other finds it.
    content_type, _ = ContentType.objects.get_or_create(
        app_label='intake',
        model='intakesubmission',
    )
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename=PERMISSION_CODENAME,
        defaults={'name': PERMISSION_NAME},
    )
    # 0007 already created the group; get_or_create so a hand-deleted group self-heals
    # rather than failing the deploy.
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.add(permission)


def revoke_status_permission(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # Detach only. The group belongs to 0007 and the permission row to 0009's Meta.
    group = Group.objects.filter(name=GROUP_NAME).first()
    permission = Permission.objects.filter(
        content_type__app_label='intake',
        content_type__model='intakesubmission',
        codename=PERMISSION_CODENAME,
    ).first()
    if group and permission:
        group.permissions.remove(permission)


class Migration(migrations.Migration):

    dependencies = [
        ('intake', '0009_alter_intakesubmission_options_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(grant_status_permission, revoke_status_permission),
    ]
