# Generated by Django 5.1.6 on 2025-05-12 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprises', '0023_reportpostentity'),
    ]

    operations = [
        migrations.AddField(
            model_name='postentity',
            name='is_remove_by_admin',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='reportpostentity',
            name='is_remove',
            field=models.BooleanField(default=False, verbose_name='Gỡ bài đăng'),
        ),
    ]
