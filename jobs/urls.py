from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('new/', views.job_create, name='create'),
    path('<uuid:pk>/', views.job_detail, name='detail'),
    path('<uuid:pk>/edit/', views.job_edit, name='edit'),
    path('<uuid:pk>/update-status/', views.update_job_status, name='update_status'),
]
