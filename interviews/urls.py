# interviews/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('interviews/', views.get_interviews, name='get-interviews'),
    path('interviews/create/', views.create_interview, name='create-interview'),
    path('interviews/<int:pk>/', views.get_interview_detail, name='get-interview-detail'),
    path('interviews/<int:pk>/update/', views.update_interview, name='update-interview'),
    path('interviews/<int:pk>/delete/', views.delete_interview, name='delete-interview'),
    path('interviews/<int:pk>/respond/', views.respond_to_interview, name='respond-to-interview'),
]