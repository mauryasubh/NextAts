from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('team/', views.team_list_view, name='team'),
    path('team/invite/', views.invite_member, name='team_invite'),
    path('team/remove/', views.remove_member, name='team_remove'),
    path('team/dept/assign/', views.assign_department_member, name='dept_assign_member'),
    path('team/dept/remove/', views.remove_department_member, name='dept_remove_member'),
    path('team/update-role/', views.update_member_role, name='team_update_role'),
    path('team/departments/', views.departments_view, name='departments'),
    path('team/departments/<uuid:dept_id>/', views.departments_view, name='departments_detail'),
    path('team/department/create/', views.department_management, name='department_manage'),
    path('team/dept/delete/', views.delete_department, name='dept_delete'),
]
