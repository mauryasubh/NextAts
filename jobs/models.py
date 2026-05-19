import uuid
from django.db import models
from users.models import Workspace

class ClientCompany(models.Model):
    """
    The external client that the agency is recruiting for.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=255)
    website = models.URLField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class JobRequisition(models.Model):
    """
    A specific job opening belonging to a Client Company.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('ENGINEERING', 'Engineering'),
        ('DESIGN', 'Design'),
        ('MARKETING', 'Marketing'),
        ('SALES', 'Sales'),
        ('OPERATIONS', 'Operations'),
        ('PRODUCT', 'Product'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    
    # AI Rules
    ai_parsing_strictness = models.IntegerField(
        default=80, 
        help_text="Thresold 1-100. How strictly the AI should match candidates to this job."
    )
    ai_condensed_requirements = models.TextField(
        blank=True, 
        null=True, 
        help_text="AI-generated summary of core requirements to save LLM tokens"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} @ {self.client_company.name}"


class JobAnalysisTask(models.Model):
    """Tracks a batch analysis run for a job."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    job = models.ForeignKey(JobRequisition, on_delete=models.CASCADE, related_name='analysis_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    total_profiles = models.IntegerField(default=0)
    processed_profiles = models.IntegerField(default=0)
    failed_profiles = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Analysis for {self.job.title} ({self.status})"

