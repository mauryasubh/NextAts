from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from .models import JobRequisition
from .services.jobs import create_job_requisition

@login_required
def job_list(request):
    category_filter = request.GET.get('category')
    sort_filter = request.GET.get('sort', 'newest')
    
    # Base Query
    jobs = JobRequisition.objects.filter(client_company__workspace=request.user.workspace)
    
    # Category Filter
    if category_filter and category_filter != 'ALL':
        jobs = jobs.filter(category=category_filter)
    
    # Sorting
    if sort_filter == 'oldest':
        jobs = jobs.order_by('created_at')
    else:
        jobs = jobs.order_by('-created_at')
    
    # Split into sections
    active_jobs = [j for j in jobs if j.status == 'ACTIVE']
    draft_jobs = [j for j in jobs if j.status == 'DRAFT']
    expired_jobs = [j for j in jobs if j.status == 'CLOSED']
    
    return render(request, 'jobs/list.html', {
        'active_jobs': active_jobs,
        'draft_jobs': draft_jobs,
        'expired_jobs': expired_jobs,
        'active_count': len(active_jobs),
        'draft_count': len(draft_jobs),
        'expired_count': len(expired_jobs),
        'category_choices': JobRequisition.CATEGORY_CHOICES,
        'current_category': category_filter or 'ALL',
        'current_sort': sort_filter
    })

@login_required
def job_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        ai_strictness = request.POST.get('ai_parsing_strictness', 80)
        status = request.POST.get('status', 'DRAFT')
        category = request.POST.get('category', 'OTHER')
        
        from .models import ClientCompany
        
        # Grab the first auto-created ClientCompany for this workspace
        client_company = request.user.workspace.clients.first()
        
        # Self-healing: If no client exists (e.g. for accounts created before the update), create one
        if not client_company:
            client_company = ClientCompany.objects.create(
                workspace=request.user.workspace,
                name="Internal Hiring"
            )

        try:
            job = create_job_requisition(
                workspace=request.user.workspace,
                client_company=client_company,
                title=title,
                description=description,
                ai_parsing_strictness=int(ai_strictness),
                status=status,
                category=category
            )
            messages.success(request, f"Job '{job.title}' created successfully!")
            return redirect('jobs:detail', pk=job.pk)
            
        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating job: {str(e)}")
            
    return render(request, 'jobs/create.html', {
        'status_choices': JobRequisition.STATUS_CHOICES,
        'category_choices': JobRequisition.CATEGORY_CHOICES
    })

@login_required
def job_edit(request, pk):
    job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        ai_strictness = request.POST.get('ai_parsing_strictness', 80)
        status = request.POST.get('status', 'DRAFT')
        category = request.POST.get('category', 'OTHER')
        
        # Check plan limits if changing TO active
        if status == 'ACTIVE' and job.status != 'ACTIVE' and not request.user.workspace.can_create_job():
            messages.error(request, "Limit reached: You cannot activate another job on your current plan.")
            return redirect('jobs:edit', pk=job.pk)

        try:
            job.title = title
            job.description = description
            job.ai_parsing_strictness = int(ai_strictness)
            job.status = status
            job.category = category
            job.save()
            
            messages.success(request, f"Job '{job.title}' updated successfully!")
            return redirect('jobs:detail', pk=job.pk)
        except Exception as e:
            messages.error(request, f"Error updating job: {str(e)}")
            
    return render(request, 'jobs/edit.html', {
        'job': job,
        'status_choices': JobRequisition.STATUS_CHOICES,
        'category_choices': JobRequisition.CATEGORY_CHOICES
    })

@login_required
def job_detail(request, pk):
    job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
    applications = job.applications.select_related('candidate').all()
    
    # Pre-compute stage counts for column headers
    sourced_count = sum(1 for a in applications if a.stage == 'SOURCED')
    interviewing_count = sum(1 for a in applications if a.stage == 'INTERVIEWING')
    offer_count = sum(1 for a in applications if a.stage in ('OFFER', 'HIRED'))
    rejected_count = sum(1 for a in applications if a.stage == 'REJECTED')
    
    return render(request, 'jobs/detail.html', {
        'job': job,
        'applications': applications,
        'sourced_count': sourced_count,
        'interviewing_count': interviewing_count,
        'offer_count': offer_count,
        'rejected_count': rejected_count,
    })

@login_required
def update_job_status(request, pk):
    """
    AJAX endpoint to update job status via Drag & Drop.
    Enforces workspace plan limits.
    """
    if request.method == 'POST':
        job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
        new_status = request.POST.get('status')
        
        if new_status in dict(JobRequisition.STATUS_CHOICES):
            # Enforce limits if moving TO active
            if new_status == 'ACTIVE' and job.status != 'ACTIVE':
                if not request.user.workspace.can_create_job():
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Limit reached: You cannot activate another job on your current plan.'
                    }, status=400)
            
            job.status = new_status
            job.save()
            return JsonResponse({'status': 'success'})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def ai_insights(request, pk):
    """AI Insights page — shows AI-driven analysis of candidates matched to this job."""
    job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
    applications = job.applications.select_related('candidate').all()
    
    analyzed_apps = [a for a in applications if a.ai_analysis_done]
    pending_apps = [a for a in applications if not a.ai_analysis_done]
    
    insights = []
    for app in analyzed_apps:
        insights.append({
            'application': app,
            'candidate': app.candidate,
            'overall_score': app.ai_match_score or 0,
            'skills_score': app.ai_skills_score or 0,
            'experience_score': app.ai_experience_score or 0,
            'culture_score': app.ai_culture_score or 0,
            'resume_score': app.ai_resume_score or 0,
            'matched_skills': app.ai_matched_skills or [],
            'missing_skills': app.ai_missing_skills or [],
            'strengths': app.ai_strengths or [],
            'gaps': app.ai_gaps or [],
            'recommendation': app.ai_recommendation or 'Pending',
            'experience_years': app.ai_experience_years or 0,
            'culture_fit': app.ai_culture_fit or 'N/A',
            'is_pending': False,
        })
    
    for app in pending_apps:
        insights.append({
            'application': app,
            'candidate': app.candidate,
            'overall_score': 0,
            'skills_score': 0,
            'experience_score': 0,
            'culture_score': 0,
            'resume_score': 0,
            'matched_skills': [],
            'missing_skills': [],
            'strengths': [],
            'gaps': [],
            'recommendation': 'Pending',
            'experience_years': 0,
            'culture_fit': 'N/A',
            'is_pending': True,
        })
    
    # Sort by score descending (ranked high to low)
    insights.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # Add rank numbers
    rank = 1
    for item in insights:
        if not item['is_pending']:
            item['rank'] = rank
            rank += 1
        else:
            item['rank'] = '-'
        
    active_task = job.analysis_tasks.filter(status='PROCESSING').first()
    
    return render(request, 'jobs/ai_insights.html', {
        'job': job,
        'insights': insights,
        'total_candidates': applications.count(),
        'analyzed_count': len(analyzed_apps),
        'pending_count': len(pending_apps),
        'is_processing': active_task is not None,
        'active_task': active_task,
    })

@login_required
def trigger_analysis(request, pk):
    if request.method == 'POST':
        job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
        from .models import JobAnalysisTask
        from .tasks import analyze_job_candidates
        
        # Check if already running
        if job.analysis_tasks.filter(status='PROCESSING').exists():
            return JsonResponse({'status': 'error', 'message': 'Analysis already running.'}, status=400)
            
        tracker = JobAnalysisTask.objects.create(job=job)
        analyze_job_candidates.delay(str(job.id), str(tracker.id))
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@login_required
def trigger_analysis_single(request, pk, app_id):
    if request.method == 'POST':
        job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
        from .tasks import analyze_single_application
        from candidates.models import Application
        
        app = get_object_or_404(Application, id=app_id, job=job)
        if not app.ai_analysis_done:
            analyze_single_application.delay(str(app.id))
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Already analyzed.'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@login_required
def analysis_status(request, pk):
    job = get_object_or_404(JobRequisition, pk=pk, client_company__workspace=request.user.workspace)
    applications = job.applications.all()
    analyzed_count = applications.filter(ai_analysis_done=True).count()
    total_count = applications.count()
    pending_count = total_count - analyzed_count
    
    active_task = job.analysis_tasks.filter(status='PROCESSING').first()
    is_processing = active_task is not None
    progress_pct = 0
    
    if is_processing and active_task.total_profiles > 0:
        # Calculate approximate progress based on pending apps delta
        initial_pending = active_task.total_profiles
        current_pending = applications.filter(ai_analysis_done=False, candidate__resume__isnull=False).exclude(candidate__resume='').count()
        processed = initial_pending - current_pending
        progress_pct = int((processed / initial_pending) * 100)
        
        if progress_pct >= 100 and current_pending > 0:
            progress_pct = 99
        elif current_pending == 0:
            progress_pct = 100
            active_task.status = 'COMPLETED'
            active_task.save(update_fields=['status'])
            is_processing = False

    return JsonResponse({
        'total': total_count,
        'analyzed': analyzed_count,
        'pending': pending_count,
        'is_processing': is_processing,
        'progress_pct': progress_pct
    })

