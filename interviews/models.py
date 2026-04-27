import uuid
from django.db import models
from django.conf import settings
from candidates.models import Application
from users.models import Workspace

class Interview(models.Model):
    TYPE_CHOICES = [
        ('SCREENING', 'Initial Screening'),
        ('TECHNICAL', 'Technical Interview'),
        ('CULTURAL', 'Cultural Fit'),
        ('FINAL', 'Final Round'),
    ]

    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="interviews")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    
    title = models.CharField(max_length=255, help_text="e.g. Technical Round with CTO")
    interview_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='TECHNICAL')
    
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="conducted_interviews"
    )
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    location_link = models.URLField(blank=True, null=True, help_text="Virtual meeting URL (Zoom, Meet, etc.)")
    feedback = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.interview_type} - {self.application.candidate}"
