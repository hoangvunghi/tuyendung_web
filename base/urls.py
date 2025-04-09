from django.contrib import admin
from django.urls import path
from .swagger import schema_view
from .aws_utils import get_all_images_from_bucket

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger',cache_timeout=0), name='schema-swagger-ui'),
    path('all-images/', get_all_images_from_bucket, name='get-all-images'),
]
