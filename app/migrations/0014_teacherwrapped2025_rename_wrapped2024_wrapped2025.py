# Generated by Django 5.0.9 on 2024-11-27 21:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_dancerequestcategory_dancerequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherWrapped2025',
            fields=[
                ('teacher_id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('name', models.TextField()),
                ('num_announcements', models.IntegerField(blank=True, null=True)),
                ('num_assignments', models.IntegerField(blank=True, null=True)),
                ('num_graded', models.IntegerField(blank=True, null=True)),
                ('num_late', models.IntegerField(blank=True, null=True)),
                ('num_zeros', models.IntegerField(blank=True, null=True)),
                ('num_canvas_minutes', models.IntegerField(blank=True, null=True)),
                ('num_canvas_clicks', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.RenameModel(
            old_name='Wrapped2024',
            new_name='Wrapped2025',
        ),
    ]
