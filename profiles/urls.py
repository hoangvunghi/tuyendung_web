# profiles/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # CV CRUD
    path('cv/', views.get_user_cvs, name='get-user-cvs'),
    path('cv/post/<int:pk>/', views.get_post_cvs, name='get-post-cvs'),
    path('cv/create/', views.create_cv, name='create-cv'),
    path('cv/<int:pk>/', views.get_cv_detail, name='get-cv-detail'),
    path('cv/<int:pk>/update/', views.update_cv, name='update-cv'),
    path('cv/<int:pk>/delete/', views.delete_cv, name='delete-cv'),
    # get_cvs_by_status
    path('cv/status/', views.get_cvs_by_status, name='get-cvs-by-status'),
    
    # CV Actions
    path('cv/<int:pk>/status/', views.update_cv_status, name='update-cv-status'),
    path('cv/<int:pk>/mark/', views.mark_cv, name='mark-cv'),
    path('cv/mark-as-viewed/<int:pk>/', views.view_cv, name='view-cv'),
    path('cv/<int:pk>/note/', views.update_cv_note, name='update-cv-note'),
    
    # profile
    path('profile/', views.get_profile, name='get-profile'),
    path('profile/update/', views.update_profile, name='update-profile'),
    path('create-user-info/', views.create_user_info, name='create-user-info'),
    
    # Premium
    path('premium/packages/', views.get_premium_packages, name='premium-packages'),
    path('premium/purchase/', views.purchase_premium, name='purchase-premium'),
    path('premium/return/', views.process_return_premium, name='process-return-premium'),
]