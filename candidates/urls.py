from django.urls import path
from . import views

app_name = 'candidates'

urlpatterns = [
    path('', views.candidate_list, name='list'),
    path('new/', views.candidate_create, name='create'),
    path('<uuid:pk>/', views.candidate_detail, name='detail'),
    path('<uuid:pk>/edit/', views.candidate_edit, name='edit'),
    path('application/<uuid:pk>/update-stage/', views.update_application_stage, name='update_stage'),
    path('application/<uuid:pk>/remove/', views.remove_from_job, name='remove_from_job'),
    path('assign-from-pool/<uuid:job_id>/', views.assign_from_pool, name='assign_from_pool'),
    path('search-pool/<uuid:job_id>/', views.search_pool, name='search_pool'),
]
