# Generated by Django 5.1.6 on 2025-03-29 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprises', '0002_alter_campaignentity_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='enterpriseentity',
            name='background_image',
            field=models.ImageField(blank=True, upload_to='enterprise_background_images/'),
        ),
    ]
