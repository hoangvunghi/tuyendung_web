# notifications/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.get_notifications, name='get-notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_as_read, name='mark-notification-read'),
    path('notifications/unread-count/', views.get_unread_count, name='get-unread-count'),
    path('websocket-test/', views.websocket_test, name='websocket-test'),
]