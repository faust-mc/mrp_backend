# Generated by Django 4.2.17 on 2025-01-14 09:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_api', '0015_roles_area'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='roles',
            name='area',
        ),
    ]
