# Generated by Django 5.1.6 on 2025-03-06 06:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('enterprises', '0001_initial'),
        ('profiles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('interview_date', models.DateTimeField()),
                ('location', models.CharField(max_length=255)),
                ('meeting_link', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Chờ phản hồi'), ('accepted', 'Đã chấp nhận'), ('rejected', 'Đã từ chối'), ('completed', 'Đã hoàn thành'), ('cancelled', 'Đã hủy')], default='pending', max_length=20)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('cv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.cv')),
                ('enterprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='enterprises.enterpriseentity')),
            ],
            options={
                'ordering': ['-interview_date'],
            },
        ),
    ]
