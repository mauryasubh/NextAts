import uuid
from django.db import models
from users.models import Workspace
from jobs.models import JobRequisition

class Candidate(models.Model):
    """
    Represents an individual person in the global talent pool for the Workspace.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('DRAFT', 'Draft'),
        ('EXPIRED', 'Expired'),
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
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="candidates")
    
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    
    # Files
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    
    # Store the parsed resume AI data
    parsed_skills = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True, null=True, help_text="AI-generated candidate summary.")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Application(models.Model):
    """
    The junction between a Candidate and a specific Job.
    Tracks pipeline progression and specific AI matching score for the role.
    """
    STAGE_CHOICES = [
        ('SOURCED', 'Sourced'),
        ('INTERVIEWING', 'Interviewing'),
        ('OFFER', 'Offer Extended'),
        ('HIRED', 'Hired'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(JobRequisition, on_delete=models.CASCADE, related_name="applications")
    
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='SOURCED')
    ai_match_score = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Match percentile (0-100) calculated by AI Engine."
    )
    
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job')

    def __str__(self):
        return f"{self.candidate} -> {self.job.title}"
