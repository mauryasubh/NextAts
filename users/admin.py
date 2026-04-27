from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Workspace, User

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'workspace', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('ATS Roles', {'fields': ('workspace', 'role')}),
    )
