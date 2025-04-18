# Generated by Django 5.1.6 on 2025-03-19 15:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='packagecampaign',
            options={'verbose_name': 'Gói đăng ký', 'verbose_name_plural': 'Gói đăng ký'},
        ),
        migrations.AlterModelOptions(
            name='packageentity',
            options={'verbose_name': 'Gói dịch vụ', 'verbose_name_plural': 'Gói dịch vụ'},
        ),
        migrations.AlterModelOptions(
            name='typeservice',
            options={'verbose_name': 'Loại dịch vụ', 'verbose_name_plural': 'Loại dịch vụ'},
        ),
        migrations.AddField(
            model_name='packagecampaign',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
