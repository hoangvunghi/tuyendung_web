# Generated by Django 5.1.6 on 2025-04-02 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprises', '0005_remove_enterpriseentity_background_image_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='enterpriseentity',
            old_name='business_certificate',
            new_name='business_certificate_public_id',
        ),
        migrations.AddField(
            model_name='enterpriseentity',
            name='business_certificate_url',
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
    ]
