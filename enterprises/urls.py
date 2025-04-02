# enterprises/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('enterprises/user/', views.get_enterprises_by_user, name='get-enterprises-by-user'),
    # Enterprise CRUD
    path('enterprises/', views.get_enterprises, name='get-enterprises'),
    path('enterprises/<int:pk>/', views.get_enterprise_detail, name='get-enterprise-detail'),
    path('enterprises/create/', views.create_enterprise, name='create-enterprise'),
    path('enterprises/<int:pk>/update/', views.update_enterprise, name='update-enterprise'),
    path('enterprises/<int:pk>/delete/', views.delete_enterprise, name='delete-enterprise'),
    path('enterprises/search/', views.search_enterprises, name='search-enterprises'),
    path('enterprises/<int:pk>/stats/', views.get_enterprise_stats, name='get-enterprise-stats'),

    # Campaign CRUD
    # path('campaigns/', views.get_campaigns, name='get-campaigns'),
    # path('campaigns/<int:pk>/', views.get_campaign_detail, name='get-campaign-detail'),
    # path('campaigns/create/', views.create_campaign, name='create-campaign'),
    # path('campaigns/<int:pk>/update/', views.update_campaign, name='update-campaign'),
    # path('campaigns/<int:pk>/delete/', views.delete_campaign, name='delete-campaign'),

    # Post CRUD
    path('posts/', views.get_posts, name='get-posts'),
    path('posts/<int:pk>/', views.get_post_detail, name='get-post-detail'),
    path('posts/create/', views.create_post, name='create-post'),
    path('posts/<int:pk>/update/', views.update_post, name='update-post'),
    path('posts/<int:pk>/delete/', views.delete_post, name='delete-post'),
    path('posts/search/', views.search_posts, name='search-posts'),
    path('posts/recommended/', views.get_recommended_posts, name='get-recommended-posts'),

    # Field Management
    path('fields/', views.get_fields, name='get-fields'),
    path('fields/create/', views.create_field, name='create-field'),
    
    # Filter Options
    path('filter-options/', views.get_filter_options, name='get-filter-options'),
]