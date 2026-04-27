from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('api/events/', views.api_interviews, name='api_events'),
    path('api/schedule/', views.api_schedule_interview, name='api_schedule'),
    path('api/cancel/<uuid:interview_id>/', views.api_cancel_interview, name='api_cancel'),
]
