# Generated by Django 5.1.6 on 2025-04-04 02:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprises', '0008_positionentity_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaignentity',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='enterpriseentity',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
