from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from .models import Candidate, Application
from jobs.models import JobRequisition
import random

@login_required
def candidate_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    workspace = request.user.workspace
    
    candidates = Candidate.objects.filter(workspace=workspace).order_by('-created_at')
    
    if query:
        candidates = candidates.filter(
            models.Q(first_name__icontains=query) | 
            models.Q(last_name__icontains=query) | 
            models.Q(email__icontains=query)
        )
    
    if category:
        candidates = candidates.filter(category=category)
    
    # Categorize for tabs
    active_candidates = candidates.filter(status='ACTIVE')
    draft_candidates = candidates.filter(status='DRAFT')
    expired_candidates = candidates.filter(status='EXPIRED')

    return render(request, 'candidates/list.html', {
        'active_candidates': active_candidates,
        'draft_candidates': draft_candidates,
        'expired_candidates': expired_candidates,
        'current_category': category,
        'search_query': query,
        'categories': Candidate.CATEGORY_CHOICES
    })

@login_required
def candidate_create(request):
    jobs = JobRequisition.objects.filter(client_company__workspace=request.user.workspace, status='ACTIVE')
    
    # Check if we're creating for a specific job
    initial_job_id = request.GET.get('job_id')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        status = request.POST.get('status', 'ACTIVE')
        category = request.POST.get('category', 'OTHER')
        job_id = request.POST.get('job_id')
        resume = request.FILES.get('resume')
        
        # 1. Create Candidate
        candidate = Candidate.objects.create(
            workspace=request.user.workspace,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            status=status,
            category=category,
            resume=resume
        )
        
        # 2. If a job is selected, create Application
        if job_id:
            job = get_object_or_404(JobRequisition, id=job_id, client_company__workspace=request.user.workspace)
            # Mock AI Match Score for demonstration
            score = random.randint(65, 99)
            Application.objects.create(
                candidate=candidate,
                job=job,
                stage='SOURCED',
                ai_match_score=score
            )
            messages.success(request, f"Candidate {candidate} added to {job.title}!")
            return redirect('jobs:detail', pk=job.id)
        
        messages.success(request, f"Candidate {candidate} created successfully!")
        return redirect('candidates:list')

    return render(request, 'candidates/create.html', {
        'jobs': jobs,
        'initial_job_id': initial_job_id,
        'status_choices': Candidate.STATUS_CHOICES,
        'category_choices': Candidate.CATEGORY_CHOICES
    })

@login_required
def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk, workspace=request.user.workspace)
    
    if request.method == 'POST':
        candidate.first_name = request.POST.get('first_name')
        candidate.last_name = request.POST.get('last_name')
        candidate.email = request.POST.get('email')
        candidate.phone = request.POST.get('phone')
        candidate.status = request.POST.get('status', candidate.status)
        candidate.category = request.POST.get('category', candidate.category)
        
        if request.FILES.get('resume'):
            candidate.resume = request.FILES.get('resume')
            
        candidate.save()
        messages.success(request, f"Candidate {candidate} updated successfully!")
        return redirect('candidates:detail', pk=candidate.id)

    return render(request, 'candidates/create.html', {
        'candidate': candidate,
        'is_edit': True,
        'status_choices': Candidate.STATUS_CHOICES,
        'category_choices': Candidate.CATEGORY_CHOICES
    })

@login_required
def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk, workspace=request.user.workspace)
    applications = candidate.applications.all()
    from_job_id = request.GET.get('from_job')
    return render(request, 'candidates/detail.html', {
        'candidate': candidate,
        'applications': applications,
        'from_job_id': from_job_id,
    })

@login_required
def update_application_stage(request, pk):
    """
    API endpoint to update application stage (useful for Kanban drag/drop mock)
    """
    if request.method == 'POST':
        application = get_object_or_404(Application, pk=pk, candidate__workspace=request.user.workspace)
        new_stage = request.POST.get('stage')
        if new_stage in dict(Application.STAGE_CHOICES):
            application.stage = new_stage
            application.save()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
@login_required
def assign_from_pool(request, job_id):
    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        job = get_object_or_404(JobRequisition, id=job_id, client_company__workspace=request.user.workspace)
        candidate = get_object_or_404(Candidate, id=candidate_id, workspace=request.user.workspace)
        
        # Prevent duplicates
        if not Application.objects.filter(candidate=candidate, job=job).exists():
            score = random.randint(65, 99)
            Application.objects.create(
                candidate=candidate,
                job=job,
                stage='SOURCED',
                ai_match_score=score
            )
            messages.success(request, f"{candidate} assigned to {job.title}")
        
        return redirect('jobs:detail', pk=job_id)
    return redirect('jobs:list')

@login_required
def search_pool(request, job_id):
    query = request.GET.get('q', '')
    workspace = request.user.workspace
    
    # Candidates in workspace NOT already applied to this job
    applied_candidate_ids = Application.objects.filter(job_id=job_id).values_list('candidate_id', flat=True)
    candidates = Candidate.objects.filter(workspace=workspace).exclude(id__in=applied_candidate_ids)
    
    if query:
        candidates = candidates.filter(
            models.Q(first_name__icontains=query) | 
            models.Q(last_name__icontains=query) | 
            models.Q(email__icontains=query)
        )
    
    results = [
        {
            'id': str(c.id),
            'name': f"{c.first_name} {c.last_name}",
            'email': c.email,
            'initials': f"{c.first_name[0]}{c.last_name[0]}"
        } for c in candidates[:10]  # Limit to 10 for performance
    ]
    return JsonResponse({'results': results})

@login_required
def remove_from_job(request, pk):
    """Remove a candidate's application from a job (delete the Application record)."""
    if request.method == 'POST':
        application = get_object_or_404(Application, pk=pk, candidate__workspace=request.user.workspace)
        application.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
