# Generated by Django 5.2.1 on 2025-05-21 22:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aitutor', '0002_conversation_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='language',
            field=models.CharField(choices=[('python', 'Python'), ('java', 'Java')], default='java', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='agent',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
