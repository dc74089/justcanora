# Generated by Django 4.2.12 on 2024-05-14 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scavenger', '0003_team_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='state',
            field=models.TextField(default='{}'),
        ),
    ]
