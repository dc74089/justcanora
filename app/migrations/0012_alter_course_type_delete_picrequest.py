# Generated by Django 5.0.7 on 2024-08-09 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_alter_course_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='type',
            field=models.CharField(choices=[('advisory', 'Advisory'), ('CS1', 'Web Dev'), ('CS2', 'Python'), ('speech', 'Public Speaking'), ('team', 'Robotics Team'), ('other', 'Other')], default='other', max_length=100),
        ),
        migrations.DeleteModel(
            name='PicRequest',
        ),
    ]
