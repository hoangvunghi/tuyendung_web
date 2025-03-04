from django.urls import path
from .views import login, register, token_refresh

urlpatterns = [
    path('api/register/', register, name='register'),
    path('api/login/', login, name='login'),
    path('api/token-refresh/', token_refresh, name='token-refresh'),
]