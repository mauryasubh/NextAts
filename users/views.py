import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Workspace, User, Department, DepartmentAllocation
from .permissions import is_global_admin, is_manager, can_invite_role, can_manage_member

@login_required
def settings_view(request):
    user = request.user
    workspace = user.workspace
    success_message = None
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        success_message = "Profile updated successfully!"

    return render(request, 'users/settings.html', {
        'workspace': workspace,
        'success_message': success_message
    })

@login_required
def team_list_view(request):
    # Only Admin, Sub-Admin, and Manager can see the team list
    if request.user.role not in ['ADMIN', 'SUB_ADMIN', 'MANAGER']:
        return HttpResponseForbidden("You do not have permission to view the team directory.")
    
    workspace = request.user.workspace
    # Ensure default departments exist
    ensure_default_departments(workspace)
    
    # Optimization: prefetch allocations and departments
    members = workspace.users.all().prefetch_related('allocations__department').order_by('role', 'date_joined')
    departments = workspace.departments.all()
    
    # Calculate total allocation percentage for each member
    for member in members:
        if member.role == 'ADMIN':
            member.total_pct = 100
        else:
            member.total_pct = sum(a.allocation_percentage for a in member.allocations.all())
        
        # Determine if current user can manage this specific member
        member.can_manage = can_manage_member(request.user, member)

    return render(request, 'users/team.html', {
        'members': members,
        'departments': departments,
        'roles': User.ROLE_CHOICES,
        'can_create_dept': is_global_admin(request.user)
    })

@login_required
def department_management(request):
    if not is_global_admin(request.user):
        return HttpResponseForbidden("Only Admins can manage departments.")
    
    workspace = request.user.workspace
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Department.objects.get_or_create(workspace=workspace, name=name)
            messages.success(request, f"Department '{name}' created.")
    
    return redirect('users:departments')

@login_required
def departments_view(request, dept_id=None):
    if request.user.role not in ['ADMIN', 'SUB_ADMIN', 'MANAGER']:
        return HttpResponseForbidden("You do not have permission to manage departments.")
    
    workspace = request.user.workspace
    departments = workspace.departments.all().prefetch_related('user_allocations__user')
    
    selected_dept = None
    if dept_id:
        selected_dept = get_object_or_404(Department, pk=dept_id, workspace=workspace)
    elif departments.exists():
        selected_dept = departments.first()
        
    # Get all users in workspace for the assignment dropdown
    # Get all users in workspace for the assignment dropdown
    members = workspace.users.all().order_by('role', 'date_joined')
    # Determine if the current user can manage the selected department
    can_manage_selected_dept = False
    if selected_dept:
        if is_global_admin(request.user):
            can_manage_selected_dept = True
        elif is_manager(request.user):
            can_manage_selected_dept = request.user.allocations.filter(department=selected_dept).exists()
    # Filter members for dropdown based on permissions
    if is_global_admin(request.user):
        members_dropdown = members
    elif is_manager(request.user):
        members_dropdown = members.exclude(role__in=['ADMIN', 'SUB_ADMIN', 'MANAGER'])
    else:
        members_dropdown = members
    
    return render(request, 'users/departments.html', {
        'departments': departments,
        'selected_dept': selected_dept,
        'members': members,
        'can_create_dept': is_global_admin(request.user),
    })

@login_required
def delete_department(request):
    if not is_global_admin(request.user):
        return HttpResponseForbidden("Only Admins can delete departments.")
    if request.method == 'POST':
        dept_id = request.POST.get('dept_id')
        try:
            dept = Department.objects.get(pk=dept_id, workspace=request.user.workspace)
            name = dept.name
            dept.delete()
            messages.success(request, f"Department '{name}' deleted.")
        except Department.DoesNotExist:
            messages.error(request, "Department not found.")
    return redirect('users:departments')

@login_required
@transaction.atomic
def invite_member(request):
    if request.method != 'POST':
        return redirect('users:team')

    inviter = request.user
    role = request.POST.get('role', 'RECRUITER')

    # 1. Permission Check
    if not can_invite_role(inviter, role):
        messages.error(request, f"You don't have permission to invite a {role}.")
        return redirect('users:team')

    email = request.POST.get('email')
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    password = request.POST.get('password')

    if User.objects.filter(email=email).exists():
        messages.error(request, f"User with email {email} already exists.")
        return redirect('users:team')

    try:
        # Create User without allocations (Decoupled Flow)
        new_user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            workspace=inviter.workspace,
            role=role
        )

        messages.success(request, f"Successfully invited {new_user.get_full_name()}! You can now assign them to departments.")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
            
    return redirect('users:team')

@login_required
def assign_department_member(request):
    """Assigns a member to a department with a specific percentage."""
    if request.method != 'POST':
        return redirect('users:team')
    
    workspace = request.user.workspace
    dept_id = request.POST.get('dept_id')
    user_id = request.POST.get('user_id')
    percentage = int(request.POST.get('percentage', 100))
    
    department = get_object_or_404(Department, pk=dept_id, workspace=workspace)
    member = get_object_or_404(User, pk=user_id, workspace=workspace)
    
    # Permissions
    if not is_global_admin(request.user):
        if is_manager(request.user):
            # Managers can only assign to their own departments
            if not request.user.allocations.filter(department=department).exists():
                return HttpResponseForbidden("You cannot manage this department.")
        else:
            return HttpResponseForbidden("No permission.")

    try:
        allocation = DepartmentAllocation(
            user=member,
            department=department,
            allocation_percentage=percentage
        )
        allocation.full_clean()
        allocation.save()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({
                'success': True,
                'message': f"Assigned {member.get_full_name()} to {department.name}."
            })
        
        messages.success(request, f"Assigned {member.get_full_name()} to {department.name}.")
        return redirect(reverse('users:departments_detail', kwargs={'dept_id': dept_id}))

    except ValidationError as e:
        error_msg = e.messages[0] if isinstance(e.messages, list) else str(e)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect(reverse('users:departments_detail', kwargs={'dept_id': dept_id}))

    except Exception as e:
        error_msg = f"Assignment failed: {str(e)}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect(reverse('users:departments_detail', kwargs={'dept_id': dept_id}))

@login_required
def remove_department_member(request):
    """Removes a member from a department."""
    if request.method != 'POST':
        return redirect('users:team')
        
    workspace = request.user.workspace
    allocation_id = request.POST.get('allocation_id')
    allocation = get_object_or_404(DepartmentAllocation, pk=allocation_id, department__workspace=workspace)
    
    # Permission (same as assign)
    if not can_manage_member(request.user, allocation.user):
        return HttpResponseForbidden("Permission denied.")
        
    name = allocation.user.get_full_name()
    dept_name = allocation.department.name
    allocation.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
        return JsonResponse({
            'success': True,
            'message': f"Removed {name} from {dept_name}."
        })
        
    messages.success(request, f"Removed {name} from {dept_name}")
    # Preserve panel state on removal too
    dept_id = allocation.department.pk
    return redirect(reverse('users:departments_detail', kwargs={'dept_id': dept_id}))

def ensure_default_departments(workspace):
    """Seeds default departments if none exist."""
    defaults = ["Engineering", "Sales", "HR", "Marketing"]
    for name in defaults:
        Department.objects.get_or_create(workspace=workspace, name=name)

@login_required
def remove_member(request):
    if request.method != 'POST':
        return redirect('users:team')
        
    member_id = request.POST.get('member_id')
    member = get_object_or_404(User, pk=member_id, workspace=request.user.workspace)
    
    # Hierarchy Check
    if not can_manage_member(request.user, member):
        messages.error(request, "You do not have permission to remove this member.")
        return redirect('users:team')
    
    # Prevent self-deletion
    if member == request.user:
        messages.error(request, "You cannot remove yourself from the workspace.")
        return redirect('users:team')
    
    name = member.get_full_name()
    member.delete()
    messages.success(request, f"Removed {name} from the team.")
    return redirect('users:team')

@login_required
def update_member_role(request):
    member_id = request.POST.get('member_id')
    member = get_object_or_404(User, pk=member_id, workspace=request.user.workspace)

    # Hierarchy Check
    if not can_manage_member(request.user, member):
        messages.error(request, "You do not have permission to change this member's role.")
        return redirect('users:team')

    # Prevent self-role change
    if member == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect('users:team')

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in [choice[0] for choice in User.ROLE_CHOICES]:
            # Additional logic: If promoting to MANAGER/ADMIN, only Global Admin can do it
            if new_role in ['ADMIN', 'SUB_ADMIN', 'MANAGER'] and not is_global_admin(request.user):
                messages.error(request, "Only Admins can promote members to management roles.")
                return redirect('users:team')
                
            member.role = new_role
            member.save()
            messages.success(request, f"Updated {member.get_full_name()}'s role to {member.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selected.")
            
    return redirect('users:team')


@login_required
def analytics_view(request):
    """
    Workspace Analytics page — high-level recruitment performance,
    AI utilization, and team overview. Restricted to Admin, Sub-Admin, Manager.
    """
    if request.user.role not in ['ADMIN', 'SUB_ADMIN', 'MANAGER']:
        return HttpResponseForbidden("You do not have permission to view analytics.")

    workspace = request.user.workspace

    from jobs.models import JobRequisition
    from candidates.models import Candidate, Application

    # ── Workspace-scoped base querysets ──
    all_jobs = JobRequisition.objects.filter(client_company__workspace=workspace)
    all_applications = Application.objects.filter(job__client_company__workspace=workspace)
    all_candidates = Candidate.objects.filter(workspace=workspace)

    # ── Section 1: KPI Cards ──
    active_jobs_count = all_jobs.filter(status='ACTIVE').count()
    pipeline_count = all_applications.exclude(stage__in=['HIRED', 'REJECTED']).count()
    hires_count = all_applications.filter(stage='HIRED').count()
    avg_hire_score = all_applications.filter(
        stage='HIRED', ai_match_score__isnull=False
    ).aggregate(avg=Avg('ai_match_score'))['avg'] or 0

    # Monthly deltas (current month vs last month)
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    hires_this_month = all_applications.filter(stage='HIRED', applied_at__gte=current_month_start).count()
    hires_last_month = all_applications.filter(
        stage='HIRED', applied_at__gte=last_month_start, applied_at__lt=current_month_start
    ).count()
    hires_delta = hires_this_month - hires_last_month

    candidates_this_month = all_candidates.filter(created_at__gte=current_month_start).count()
    candidates_last_month = all_candidates.filter(
        created_at__gte=last_month_start, created_at__lt=current_month_start
    ).count()
    candidates_delta = candidates_this_month - candidates_last_month

    # ── Section 2: Recruitment Funnel ──
    funnel_data = {
        'Sourced': all_applications.filter(stage='SOURCED').count(),
        'Interviewing': all_applications.filter(stage='INTERVIEWING').count(),
        'Offer': all_applications.filter(stage='OFFER').count(),
        'Hired': hires_count,
        'Rejected': all_applications.filter(stage='REJECTED').count(),
    }

    # ── Section 3: Hiring Trend — precompute ALL ranges for client-side switching ──
    all_trend_data = {}
    for num_months in [3, 6, 12]:
        labels = []
        apps_data = []
        hires_data = []
        for i in range(num_months - 1, -1, -1):
            dt = now - timedelta(days=i * 30)
            month_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                next_dt = now - timedelta(days=(i - 1) * 30)
                month_end = next_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            labels.append(month_start.strftime('%b %Y'))
            apps_data.append(
                all_applications.filter(applied_at__gte=month_start, applied_at__lt=month_end).count()
            )
            hires_data.append(
                all_applications.filter(
                    stage='HIRED', applied_at__gte=month_start, applied_at__lt=month_end
                ).count()
            )
        all_trend_data[str(num_months)] = {
            'labels': labels,
            'applications': apps_data,
            'hires': hires_data,
        }

    # ── Section 4: AI Engine Performance ──
    total_with_resume = all_applications.filter(
        candidate__resume__isnull=False
    ).exclude(candidate__resume='').count()
    ai_analyzed_count = all_applications.filter(ai_analysis_done=True).count()
    ai_success_rate = round((ai_analyzed_count / total_with_resume * 100), 1) if total_with_resume > 0 else 0
    ai_avg_score = all_applications.filter(
        ai_analysis_done=True, ai_match_score__isnull=False
    ).aggregate(avg=Avg('ai_match_score'))['avg'] or 0

    # ── Section 5: Jobs by Category (Doughnut) ──
    category_qs = all_jobs.exclude(status='CLOSED').values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    category_labels = []
    category_counts = []
    category_map = dict(JobRequisition.CATEGORY_CHOICES)
    for item in category_qs:
        category_labels.append(category_map.get(item['category'], item['category']))
        category_counts.append(item['count'])
    category_data = {'labels': category_labels, 'counts': category_counts}

    # ── Section 6: AI Score Distribution (Bar) ──
    scored_apps = all_applications.filter(ai_analysis_done=True, ai_match_score__isnull=False)
    score_dist = {
        '0–40 (Weak)': scored_apps.filter(ai_match_score__lt=40).count(),
        '40–60 (Average)': scored_apps.filter(ai_match_score__gte=40, ai_match_score__lt=60).count(),
        '60–80 (Strong)': scored_apps.filter(ai_match_score__gte=60, ai_match_score__lt=80).count(),
        '80–100 (Excellent)': scored_apps.filter(ai_match_score__gte=80).count(),
    }

    # ── Section 7: Top 5 Jobs by Applicants ──
    top_jobs = all_jobs.filter(status='ACTIVE').annotate(
        app_count=Count('applications'),
        avg_score=Avg('applications__ai_match_score')
    ).order_by('-app_count')[:5]

    # ── Section 6: Team Overview ──
    team_members = workspace.users.all().prefetch_related(
        'allocations__department'
    ).order_by('role', 'date_joined')[:8]

    for member in team_members:
        if member.role == 'ADMIN':
            member.total_pct = 100
        else:
            member.total_pct = sum(a.allocation_percentage for a in member.allocations.all())
        member.dept_names = ', '.join(
            a.department.name for a in member.allocations.all()
        ) or '—'

    # ── Quarter-wise Growth Stats ──
    current_month = now.month
    current_year = now.year
    # Determine current quarter start
    quarter_start_month = ((current_month - 1) // 3) * 3 + 1
    quarter_start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    # Previous quarter
    prev_quarter_end = quarter_start
    prev_quarter_start_month = ((quarter_start_month - 4) % 12) + 1
    prev_quarter_year = current_year if quarter_start_month > 3 else current_year - 1
    prev_quarter_start = now.replace(year=prev_quarter_year, month=prev_quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)

    quarter_apps = all_applications.filter(applied_at__gte=quarter_start).count()
    prev_quarter_apps = all_applications.filter(applied_at__gte=prev_quarter_start, applied_at__lt=prev_quarter_end).count()
    quarter_app_growth = round(((quarter_apps - prev_quarter_apps) / prev_quarter_apps * 100)) if prev_quarter_apps > 0 else (100 if quarter_apps > 0 else 0)

    quarter_hires = all_applications.filter(stage='HIRED', applied_at__gte=quarter_start).count()
    prev_quarter_hires = all_applications.filter(stage='HIRED', applied_at__gte=prev_quarter_start, applied_at__lt=prev_quarter_end).count()
    quarter_hire_growth = round(((quarter_hires - prev_quarter_hires) / prev_quarter_hires * 100)) if prev_quarter_hires > 0 else (100 if quarter_hires > 0 else 0)

    context = {
        # KPIs
        'active_jobs_count': active_jobs_count,
        'pipeline_count': pipeline_count,
        'hires_count': hires_count,
        'avg_hire_score': round(avg_hire_score),
        'hires_delta': hires_delta,
        'candidates_delta': candidates_delta,
        'total_candidates_count': all_candidates.count(),
        # Funnel
        'funnel_json': json.dumps(funnel_data),
        # Trend (all ranges for client-side switching)
        'all_trend_json': json.dumps(all_trend_data),
        # Charts
        'category_json': json.dumps(category_data),
        'score_dist_json': json.dumps(score_dist),
        # AI
        'ai_analyzed_count': ai_analyzed_count,
        'ai_success_rate': ai_success_rate,
        'ai_avg_score': round(ai_avg_score),
        # Top Jobs
        'top_jobs': top_jobs,
        # Team
        'team_members': team_members,
        # Quarter Stats
        'quarter_apps': quarter_apps,
        'prev_quarter_apps': prev_quarter_apps,
        'quarter_app_growth': quarter_app_growth,
        'quarter_hires': quarter_hires,
        'prev_quarter_hires': prev_quarter_hires,
        'quarter_hire_growth': quarter_hire_growth,
    }

    return render(request, 'users/analytics.html', context)

