from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import ValidationError
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
