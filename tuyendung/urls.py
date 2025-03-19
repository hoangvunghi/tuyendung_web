from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from .swagger import urlpatterns as swagger_urls

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
    
    # API Documentation
    path('api-docs/', include(swagger_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
