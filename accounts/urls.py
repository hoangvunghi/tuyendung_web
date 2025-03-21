from django.urls import path
from .views import login, register, token_refresh,forgot_password_view,reset_password_view
from . import views
urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('activate/<str:token>/', views.activate_account, name='activate_account'),
    path('token-refresh/', token_refresh, name='token-refresh'),
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('reset-password/', reset_password_view, name='reset-password'),
    path('resend-activation/', views.resend_activation_email, name='resend_activation'),
]