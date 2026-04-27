from django.contrib import admin
from .models import Candidate, Application

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'workspace')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'stage', 'ai_match_score', 'applied_at')
    list_filter = ('stage', 'job')
