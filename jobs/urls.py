from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('new/', views.job_create, name='create'),
    path('<uuid:pk>/', views.job_detail, name='detail'),
    path('<uuid:pk>/edit/', views.job_edit, name='edit'),
    path('<uuid:pk>/update-status/', views.update_job_status, name='update_status'),
    path('<uuid:pk>/ai-insights/', views.ai_insights, name='ai_insights'),
    path('<uuid:pk>/trigger-analysis/', views.trigger_analysis, name='trigger_analysis'),
    path('<uuid:pk>/trigger-analysis-single/<uuid:app_id>/', views.trigger_analysis_single, name='trigger_analysis_single'),
    path('<uuid:pk>/analysis-status/', views.analysis_status, name='analysis_status'),
]
