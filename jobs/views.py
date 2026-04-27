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
    return render(request, 'jobs/detail.html', {
        'job': job,
        'applications': applications
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
