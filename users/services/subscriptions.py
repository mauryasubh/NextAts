from datetime import timedelta
from django.utils import timezone
from users.models import Workspace

def init_workspace_trial(workspace: Workspace):
    """
    Called when a new workspace is created.
    Assigns a 14-day Growth plan trial by default.
    """
    workspace.plan = 'GROWTH'
    workspace.subscription_status = 'TRIAL'
    workspace.trial_ends_at = timezone.now() + timedelta(days=14)
    workspace.save()

def set_starter_plan(workspace: Workspace):
    """
    Downgrades a workspace to the free Starter plan.
    """
    workspace.plan = 'STARTER'
    workspace.subscription_status = 'ACTIVE'
    workspace.trial_ends_at = None
    workspace.save()

from django.db import transaction
from users.models import User
from jobs.models import ClientCompany

def provision_new_tenant(*, company_name: str, first_name: str, last_name: str, email: str, password: str, plan: str = 'starter') -> User:
    """
    Creates a new Workspace for the company, creates the founding Admin user,
    and initializes their plan (Starter or Growth Trial). Atomic transaction ensures both succeed or fail together.
    """
    with transaction.atomic():
        workspace = Workspace.objects.create(name=company_name)
        
        # Auto-create an internal client so they can post jobs immediately
        ClientCompany.objects.create(
            workspace=workspace,
            name="Internal Hiring"
        )
        
        if plan == 'growth':
            init_workspace_trial(workspace)
        else:
            set_starter_plan(workspace)
        
        user = User.objects.create_user(
            username=email, # Using email as username
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            workspace=workspace,
            role='ADMIN'
        )
        return user
