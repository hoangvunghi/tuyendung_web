# enterprises/urls.py
from django.urls import path
from . import views
from .report_views import report_post, get_user_reports

urlpatterns = [
    path('enterprises/user/', views.get_enterprises_by_user, name='get-enterprises-by-user'),
    # Enterprise CRUD
    path('enterprises/', views.get_enterprises, name='get-enterprises'),
    path('enterprises/<int:pk>/', views.get_enterprise_detail, name='get-enterprise-detail'),
    path('enterprises/create/', views.create_enterprise, name='create-enterprise'),
    path('enterprises/update/', views.update_enterprise, name='update-enterprise'),
    path('enterprises/<int:pk>/delete/', views.delete_enterprise, name='delete-enterprise'),
    path('enterprises/search/', views.search_enterprises, name='search-enterprises'),
    path('enterprises/<int:pk>/stats/', views.get_enterprise_stats, name='get-enterprise-stats'),
    path('enterprises/premium/', views.get_enterprise_premium, name='get-enterprise-premium'),
    # Post CRUD
    path('posts/', views.get_posts, name='get-posts'),
    path('post/<int:pk>/', views.get_post_detail, name='get-post-detail'),
    path('posts/create/', views.create_post, name='create-post'),
    path('posts/update/<int:pk>/', views.update_post, name='update-post'),
    path('posts/delete/<int:pk>/', views.delete_post, name='delete-post'),
    path('posts/search/', views.search_posts, name='search-posts'),
    path('posts/recommended/', views.get_recommended_posts, name='get-recommended-posts'),
    path('posts/all/', views.get_all_posts, name='get-all-posts'),
    path('posts/enterprise/', views.get_post_for_enterprise, name='get-post-of-enterprise'),
    path('posts/enterprise/<int:pk>/', views.get_posts_for_enterprise_detail, name='get-post-of-enterprise-detail'),
    path('posts/user/', views.get_post_of_user, name='get-post-of-user'),
    path('post/<int:pk>/toggle-status/', views.toogle_post_status, name='toggle-post-status'),
    path('post/enterprise/<int:pk>/', views.get_enterprise_post_detail, name='get_enterprise_post_detail'),
    # Field Management
    path('fields/', views.get_fields, name='get-fields'),
    path('fields/create/', views.create_field, name='create-field'),
    path('fields/<int:field_id>/', views.get_field_name, name='get-field-name'),
 

    # Position URLs
    path('positions/', views.get_positions, name='get_positions'),
    path('positions/create/', views.create_position, name='create_position'),
    path('positions/<int:pk>/', views.update_position, name='update_position'),
    path('positions/<int:pk>/delete/', views.delete_position, name='delete_position'),
    path('positions/field/<int:field_id>/', views.get_positions_by_field, name='get_positions_by_field'),
    path('position/<int:pk>/', views.get_position_name, name='get_position_name'),
    # Criteria URLs
    path('criteria/', views.get_criteria, name='get_criteria'),
    path('criteria/create/', views.create_criteria, name='create_criteria'),
    path('criteria/update/', views.update_criteria, name='update_criteria'),
    path('criteria/delete/', views.delete_criteria, name='delete_criteria'),
    path('statistics/', views.enterprise_statistics, name='enterprise_statistics'),
    
    # SavedPost URLs
    path('saved-posts/', views.get_saved_posts, name='get_saved_posts'),
    path('saved-posts/save/', views.save_post, name='save_post'),
    path('saved-posts/<int:pk>/delete/', views.delete_saved_post, name='delete_saved_post'),
    path('saved-posts/post/<int:post_id>/delete/', views.delete_saved_post_by_post_id, name='delete_saved_post_by_post_id'),
    path('saved-posts/post/<int:post_id>/check/', views.check_post_saved, name='check_post_saved'),
    # Report Post URLs
    path('posts/report/', report_post, name='report_post'),
    path('user-reports/', get_user_reports, name='get_user_reports'),
]