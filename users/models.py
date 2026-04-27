import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class Workspace(models.Model):
    """
    The top-level Tenant for an Agency.
    All data in the system must be linked back to a Workspace to ensure isolation.
    """
    PLAN_CHOICES = [
        ('STARTER', 'Starter (Free)'),
        ('GROWTH', 'Growth'),
        ('ENTERPRISE', 'Enterprise'),
    ]

    STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
        ('ACTIVE', 'Active'),
        ('PAST_DUE', 'Past Due'),
        ('CANCELED', 'Canceled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g. Metrix Recruitment Agency")
    
    # Subscription Fields
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='STARTER')
    subscription_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TRIAL')
    plan_started_at = models.DateTimeField(auto_now_add=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def can_create_job(self):
        """
        Check if the workspace can create a new job requisition based on its plan.
        Starter: Max 2 active jobs.
        Growth/Enterprise: Unlimited for now.
        """
        if self.plan == 'STARTER':
            active_jobs_count = self.clients.filter(jobs__status='ACTIVE').count()
            return active_jobs_count < 2
        return True

class Department(models.Model):
    """
    Groups users within a Workspace.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'name')

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"

class User(AbstractUser):
    """
    Custom user model attached to a specific Workspace.
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Admin/Owner'),
        ('SUB_ADMIN', 'Sub-Admin'),
        ('MANAGER', 'Manager'),
        ('RECRUITER', 'Recruiter'),
        ('INTERVIEWER', 'Interviewer'),
    ]

    workspace = models.ForeignKey(
        Workspace, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="users"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RECRUITER')

    # Making email unique and required is best practice for SaaS
    email = models.EmailField(unique=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

class DepartmentAllocation(models.Model):
    """
    Links a User to a Department with a specific allocation percentage.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="allocations")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="user_allocations")
    allocation_percentage = models.PositiveIntegerField(default=100)

    class Meta:
        unique_together = ('user', 'department')

    def __str__(self):
        return f"{self.user.email} - {self.department.name} ({self.allocation_percentage}%)"

    def clean(self):
        # 1. Total Capacity Check (Global Admins/Admins are exempt)
        if self.user.role != 'ADMIN':
            total_allocation = DepartmentAllocation.objects.filter(
                user=self.user
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('allocation_percentage')
            )['total'] or 0

            if total_allocation + self.allocation_percentage > 100:
                raise ValidationError(
                    f"Total allocation for this user ({self.user.get_full_name()}) cannot exceed 100%. "
                    f"Current total: {total_allocation}%"
                )

        # 2. Role Uniqueness Check (Max 1 Sub-Admin and 1 Manager per Department)
        if self.user.role in ['SUB_ADMIN', 'MANAGER']:
            # Check if anyone else with this role is already in this department
            existing_role_holder = DepartmentAllocation.objects.filter(
                department=self.department,
                user__role=self.user.role
            ).exclude(user=self.user).exists()

            if existing_role_holder:
                raise ValidationError(
                    f"This department already has a {self.user.get_role_display()}. "
                    "Only one management role of each type is allowed per department."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
