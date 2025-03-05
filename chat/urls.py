# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('messages/', views.get_messages, name='get-messages'),
    path('messages/send/', views.send_message, name='send-message'),
    path('messages/unread/', views.get_unread_messages, name='get-unread-messages'),
    path('messages/<int:pk>/read/', views.mark_message_read, name='mark-message-read'),
    path('conversations/', views.get_conversations, name='get-conversations'),
]