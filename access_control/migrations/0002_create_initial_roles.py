from django.db import migrations


INITIAL_ROLES = (
    ("user", "Пользователь"),
    ("admin", "Администратор"),
)


def create_initial_roles(apps, schema_editor):
    Role = apps.get_model("access_control", "Role")

    for code, name in INITIAL_ROLES:
        Role.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [
        ("access_control", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_initial_roles, migrations.RunPython.noop),
    ]
