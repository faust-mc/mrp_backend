# Generated by Django 4.2.17 on 2024-12-26 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_api', '0004_remove_employee_department_employee_department'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModulePermissions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('codename', models.CharField(max_length=80)),
                ('content_type_id', models.IntegerField()),
            ],
        ),
    ]
