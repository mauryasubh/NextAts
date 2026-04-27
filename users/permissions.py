from .models import User, DepartmentAllocation

def is_global_admin(user):
    """
    Returns True if user is ADMIN or SUB_ADMIN.
    """
    return user.is_authenticated and user.role in ['ADMIN', 'SUB_ADMIN']

def is_manager(user):
    """
    Returns True if user is a MANAGER.
    """
    return user.is_authenticated and user.role == 'MANAGER'

def get_user_departments(user):
    """
    Returns a queryset of departments the user is allocated to.
    """
    return user.allocations.values_list('department_id', flat=True)

def can_manage_member(manager, member, department=None):
    """
    Checks if a manager (ADMIN, SUB_ADMIN, or MANAGER) can manage another member.
    Optional `department` argument enforces department‑specific manager rights.
    """
    if is_global_admin(manager):
        return True

    if not is_manager(manager):
        return False

    # Managers can manage recruiters/interviewers only
    if member.role not in ['RECRUITER', 'INTERVIEWER']:
        return False

    # If a department is supplied, ensure manager belongs to it
    if department:
        return manager.allocations.filter(department=department).exists()

    # Fallback: shared department check (kept for backward compatibility)
    manager_deps = set(get_user_departments(manager))
    member_deps = set(get_user_departments(member))
    return bool(manager_deps.intersection(member_deps))
    """
    Checks if a manager (ADMIN, SUB_ADMIN, or MANAGER) can manage another member.
    """
    if is_global_admin(manager):
        return True
    
    if not is_manager(manager):
        return False

    # Managers can manage recruiters/interviewers who share at least one department
    if member.role not in ['RECRUITER', 'INTERVIEWER']:
        return False

    manager_deps = set(get_user_departments(manager))
    member_deps = set(get_user_departments(member))
    
    return bool(manager_deps.intersection(member_deps))

def can_invite_role(inviter, role_to_invite):
    """
    Validation logic for who can invite which role.
    """
    if is_global_admin(inviter):
        return True
    
    if is_manager(inviter):
        return role_to_invite in ['RECRUITER', 'INTERVIEWER']
    
    return False
