from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Tuyendung API",
        default_version='v1',
        description="API documentation for Tuyendung project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@tuyendung.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include([
        path('', include('enterprises.urls')),
        path('', include('profiles.urls')),
        path('', include('interviews.urls')),
        path('', include('chat.urls')),
        path('', include('notifications.urls')),
        path('', include('accounts.urls')),
        path('', include('services.urls')),
        path('', include('transactions.urls')),
        path('auth/', include('social_django.urls', namespace='social')),  # Social auth URLs
    ])),
    
    # Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
