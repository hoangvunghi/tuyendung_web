from django.urls import path
from .views import (
    login, register, token_refresh, forgot_password_view, 
    reset_password_view, social_auth_token,
    complete_google_profile, SetUserRoleView
)
from . import views

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('activate/<str:token>/', views.activate_account, name='activate_account'),
    path('token-refresh/', token_refresh, name='token-refresh'),
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('reset-password/', reset_password_view, name='reset-password'),
    path('resend-activation/', views.resend_activation_email, name='resend_activation'),
    path('social-token/', social_auth_token, name='social-auth-token'),
    path('complete-google-profile/', complete_google_profile, name='complete-google-profile'),
    path('auth/social/complete', views.social_auth_complete_redirect, name='social_auth_complete_redirect'),
    path('set-role/', SetUserRoleView.as_view(), name='set_user_role'),
]