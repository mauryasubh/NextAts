from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError

from .models import ContactRequest
from users.services.subscriptions import provision_new_tenant
from jobs.models import JobRequisition
from candidates.models import Candidate, Application
from interviews.models import Interview
from django.utils import timezone
from datetime import timedelta

def index(request):
    return render(request, 'frontend/index.html')

def pricing(request):
    return render(request, 'frontend/pricing.html')

def signup(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        company_name = request.POST.get('company_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        plan = request.POST.get('plan', 'starter')

        try:
            user = provision_new_tenant(
                company_name=company_name,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                plan=plan
            )
            # Log the user in
            auth_login(request, user)
            return redirect('frontend:dashboard')
        except IntegrityError:
            # Handle duplicate email
            messages.error(request, "An account with this email already exists.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    selected_plan = request.GET.get('plan', 'starter')
    return render(request, 'frontend/signup.html', {'selected_plan': selected_plan})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('frontend:dashboard')
        else:
            messages.error(request, "Invalid credentials or account does not exist.")

    return render(request, 'frontend/login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('frontend:index')

@login_required
def dashboard(request):
    """
    Main workspace dashboard showing real-time metrics and pipeline snapshots.
    """
    workspace = request.user.workspace
    
    # 1. Key Metrics
    active_jobs = JobRequisition.objects.filter(client_company__workspace=workspace, status='ACTIVE')
    active_jobs_count = active_jobs.count()
    
    total_candidates = Candidate.objects.filter(workspace=workspace)
    total_candidates_count = total_candidates.count()
    
    # New candidates this week
    week_ago = timezone.now() - timedelta(days=7)
    new_candidates_count = total_candidates.filter(created_at__gte=week_ago).count()
    
    # 2. Pipeline Snapshot (Latest Active Job)
    snapshot_job = active_jobs.order_by('-created_at').first()
    snapshot_sourced = []
    snapshot_interviewing = []
    
    if snapshot_job:
        apps = snapshot_job.applications.all()
        snapshot_sourced = apps.filter(stage='SOURCED')[:5]
        snapshot_interviewing = apps.filter(stage='INTERVIEWING')[:5]
    
    # 3. Recent Activity (latest applications)
    recent_applications = Application.objects.filter(job__client_company__workspace=workspace).order_by('-applied_at')[:5]
    
    # 4. Today's Interviews
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_interviews = Interview.objects.filter(
        workspace=workspace,
        start_time__range=(today_start, today_end)
    ).order_by('start_time')

    context = {
        'active_jobs_count': active_jobs_count,
        'total_candidates_count': total_candidates_count,
        'new_candidates_count': new_candidates_count,
        'snapshot_job': snapshot_job,
        'snapshot_sourced': snapshot_sourced,
        'snapshot_interviewing': snapshot_interviewing,
        'recent_applications': recent_applications,
        'today_interviews': today_interviews,
    }
    
    return render(request, 'frontend/dashboard.html', context)

from users.services.subscriptions import init_workspace_trial

@login_required
def upgrade_plan(request):
    """
    Endpoint to trigger an upgrade to the Growth Trial from the Starter plan.
    """
    if request.method == 'POST':
        workspace = request.user.workspace
        if workspace and workspace.plan == 'STARTER':
            init_workspace_trial(workspace)
            messages.success(request, "Successfully upgraded to Growth! Your 14-day free trial has started.")
        else:
            messages.error(request, "Invalid upgrade request.")
            
    return redirect('frontend:dashboard')

def contact_sales(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        company_name = request.POST.get('company_name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # In a real app, you'd send an email to sales@nexats.com here
        # For now, we store in DB and show a success message
        ContactRequest.objects.create(
            name=name,
            company_name=company_name,
            email=email,
            message=message
        )
        
        messages.success(request, "Your inquiry has been received. Our sales team will reach out shortly!")
        return render(request, 'frontend/contact_sales_success.html')
        
    return render(request, 'frontend/contact_sales.html')
