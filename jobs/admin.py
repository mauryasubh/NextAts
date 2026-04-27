from django.contrib import admin
from .models import ClientCompany, JobRequisition

@admin.register(ClientCompany)
class ClientCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'created_at')

@admin.register(JobRequisition)
class JobRequisitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'client_company', 'status', 'ai_parsing_strictness')
    list_filter = ('status', 'client_company')
