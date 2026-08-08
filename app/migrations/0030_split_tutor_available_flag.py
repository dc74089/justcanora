from django.db import migrations

OLD_FLAG = "tutor_available"
NEW_FLAGS = [
    "tutor_available_apcsa",
    "tutor_available_cs2",
    "tutor_available_cs1",
]


def split_flag(apps, schema_editor):
    """Replace the single tutor kill switch with one per course.

    Each new flag inherits the old flag's value so access doesn't silently change
    across the deploy. Creating the rows here (rather than lazily) is also what
    makes them show up on the staff admin page, which lists existing flags.
    """
    FeatureFlag = apps.get_model("app", "FeatureFlag")

    old = FeatureFlag.objects.filter(id=OLD_FLAG).first()
    was_enabled = bool(old.enabled) if old else False

    for flag_id in NEW_FLAGS:
        FeatureFlag.objects.get_or_create(id=flag_id, defaults={"enabled": was_enabled})

    if old:
        old.delete()


def merge_flag(apps, schema_editor):
    """Collapse back to one flag, on if any course had it on."""
    FeatureFlag = apps.get_model("app", "FeatureFlag")

    any_enabled = FeatureFlag.objects.filter(id__in=NEW_FLAGS, enabled=True).exists()
    FeatureFlag.objects.get_or_create(id=OLD_FLAG, defaults={"enabled": any_enabled})
    FeatureFlag.objects.filter(id__in=NEW_FLAGS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0029_alter_sharkproject_year"),
    ]

    operations = [
        migrations.RunPython(split_flag, merge_flag),
    ]
