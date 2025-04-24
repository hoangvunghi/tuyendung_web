from django.urls import path
from . import views

urlpatterns = [
    # API cho thống kê doanh nghiệp
    path('enterprise/overview/', views.get_enterprise_overview, name='enterprise_overview'),
    path('enterprise/posts/time/', views.get_post_stats_by_time, name='post_stats_by_time'),
    path('enterprise/cvs/time/', views.get_cv_stats_by_time, name='cv_stats_by_time'),
    path('enterprise/posts/performance/', views.get_post_performance, name='post_performance'),
    path('enterprise/cvs/approval/', views.get_cv_approval_stats, name='cv_approval_stats'),
] 