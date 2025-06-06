# Generated by Django 5.1.6 on 2025-04-22 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_useraccount_premium_expiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='cv_views_today',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='job_applications_today',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='last_application_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='last_cv_view_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useraccount',
            name='post_count',
            field=models.IntegerField(default=0),
        ),
    ]
