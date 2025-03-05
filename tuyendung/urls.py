from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('', include('enterprises.urls')),
        path('', include('profiles.urls')),
        path('', include('interviews.urls')),
        path('', include('chat.urls')),
        path('', include('notifications.urls')),
        
        path('', include('accounts.urls')),
        path('', include('services.urls')),
        path('', include('transactions.urls')),

        
    ])),
    path('', include('base.urls')),
]
