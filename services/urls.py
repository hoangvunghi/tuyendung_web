from django.urls import path
from . import views

urlpatterns = [
    # TypeService URLs
    path('api/type-services/', views.get_type_services, name='get-type-services'),
    path('api/type-services/<int:pk>/', views.get_type_service_detail, name='get-type-service-detail'),
    path('api/type-services/create/', views.create_type_service, name='create-type-service'),
    
    # Package URLs
    path('api/packages/', views.get_packages, name='get-packages'),
    path('api/packages/create/', views.create_package, name='create-package'),
    
    # PackageCampaign URLs
    path('api/campaign-packages/', views.get_campaign_packages, name='get-campaign-packages'),
    path('api/campaign-packages/subscribe/', views.subscribe_package, name='subscribe-package'),
] 