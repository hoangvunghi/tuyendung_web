# Generated by Django 5.1.6 on 2025-04-05 02:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprises', '0011_postentity_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enterpriseentity',
            name='field_of_activity',
            field=models.TextField(),
        ),
    ]
