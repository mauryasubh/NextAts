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
    resume_text = models.TextField(blank=True, null=True, help_text="Cached parsed text from the resume.")
    resume_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 hash of the resume to detect changes.")
    
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
    
    # AI Analysis tracking
    ai_analysis_done = models.BooleanField(default=False)
    ai_analysis_started_at = models.DateTimeField(null=True, blank=True)
    ai_analysis_completed_at = models.DateTimeField(null=True, blank=True)
    ai_analysis_error = models.TextField(blank=True, null=True)

    # Detailed AI results (replaces dummy data)
    ai_skills_score = models.IntegerField(null=True, blank=True)
    ai_experience_score = models.IntegerField(null=True, blank=True)
    ai_culture_score = models.IntegerField(null=True, blank=True)
    ai_resume_score = models.IntegerField(null=True, blank=True)
    ai_matched_skills = models.JSONField(default=list, blank=True)
    ai_missing_skills = models.JSONField(default=list, blank=True)
    ai_strengths = models.JSONField(default=list, blank=True)
    ai_gaps = models.JSONField(default=list, blank=True)
    ai_recommendation = models.CharField(max_length=50, blank=True, null=True)
    ai_experience_years = models.IntegerField(null=True, blank=True)
    ai_culture_fit = models.CharField(max_length=20, blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)
    
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job')

    def __str__(self):
        return f"{self.candidate} -> {self.job.title}"
