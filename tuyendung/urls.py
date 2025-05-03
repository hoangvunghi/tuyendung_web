from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import HttpResponseRedirect
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from accounts.views import FinalizeGoogleAuthView
from . import views

# Cấu hình Swagger
schema_view = get_schema_view(
   openapi.Info(
      title="CDTN API",
      default_version='v1',
      description="API Documentation for CDTN Project",
      terms_of_service="https://www.yourapp.com/terms/",
      contact=openapi.Contact(email="contact@yourapp.com"),
      license=openapi.License(name="Your License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# Hàm chuyển hướng về frontend cho các route thanh toán
def redirect_to_frontend(request, path):
    query_string = f'?{request.GET.urlencode()}' if request.GET else ''
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/{path}{query_string}")

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include([
        path('', include('enterprises.urls')),
        path('', include('profiles.urls')),
        path('', include('transactions.urls')),
        path('', include('accounts.urls')),
        path('', include('notifications.urls')),
        path('', include('interviews.urls')),
        path('', include('chat.urls')),
        path('gemini-chat/', include('gemini_chat.urls')),  # Thêm đường dẫn cho Gemini Chat API
        # path('', include('services.urls')),
        path('auth/', include('social_django.urls', namespace='social')),  # Social auth URLs
        path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),  # Dashboard API
    ])),
    
    # Route cho payment-success và payment-failed, chuyển hướng về frontend
    path('payment-success/', lambda request: redirect_to_frontend(request, 'payment-success')),
    path('payment-failed/', lambda request: redirect_to_frontend(request, 'payment-failed')),
    
    # Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/auth/callback/', FinalizeGoogleAuthView.as_view(), name='google_auth_callback'),
    
    # Media files
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
