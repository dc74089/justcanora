import uuid

from django.db import migrations, models


def populate_direct_links(apps, schema_editor):
    Wrapped = apps.get_model('wrapped', 'Wrapped')
    for wrapped in Wrapped.objects.filter(direct_link__isnull=True):
        wrapped.direct_link = uuid.uuid4()
        wrapped.save(update_fields=['direct_link'])


class Migration(migrations.Migration):

    dependencies = [
        ('wrapped', '0004_wrapped_longest_question_wrapped_num_questions_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='wrapped',
            name='direct_link',
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_direct_links, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='wrapped',
            name='direct_link',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
