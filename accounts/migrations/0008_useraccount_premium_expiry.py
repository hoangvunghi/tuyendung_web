# Generated by Django 5.1.6 on 2025-04-19 03:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_useraccount_is_premium'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='premium_expiry',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
