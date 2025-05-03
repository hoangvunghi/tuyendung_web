from django.urls import path
from . import views

app_name = 'gemini_chat'

urlpatterns = [
    # Chat API
    path('send-message/', views.send_message, name='send_message'),
    path('sessions/', views.get_chat_sessions, name='get_chat_sessions'),
    path('sessions/create/', views.create_chat_session, name='create_chat_session'),
    path('sessions/<str:session_id>/', views.get_chat_session, name='get_chat_session'),
    path('sessions/<str:session_id>/delete/', views.delete_chat_session, name='delete_chat_session'),
    path('sessions/<str:session_id>/close/', views.close_chat_session, name='close_chat_session'),
    path('sessions/<str:session_id>/update-title/', views.update_chat_session_title, name='update_chat_session_title'),
    
    # Demo API (không yêu cầu đăng nhập)
    # path('demo/', views.demo_chat, name='demo_chat'),
] 