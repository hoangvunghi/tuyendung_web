from django.urls import path
from .views import login, register, token_refresh,forgot_password_view,reset_password_view
from . import views
urlpatterns = [
    path('api/register/', register, name='register'),
    path('api/login/', login, name='login'),
    path('activate/<str:token>/', views.activate_account, name='activate_account'),
    path('api/token-refresh/', token_refresh, name='token-refresh'),
    path('api/forgot-password/', forgot_password_view, name='forgot-password'),
    path('api/reset-password/', reset_password_view, name='reset-password'),
]