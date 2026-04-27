from django.core.exceptions import PermissionDenied
from jobs.models import JobRequisition, ClientCompany
from users.models import Workspace

def create_job_requisition(
    *, 
    workspace: Workspace,
    client_company: ClientCompany,
    title: str,
    description: str,
    ai_parsing_strictness: int = 80,
    status: str = 'DRAFT',
    category: str = 'OTHER'
) -> JobRequisition:
    """
    Service to create a new job requisition with plan limit checks.
    """
    # 1. Check if the workspace belongs to the client company
    if client_company.workspace != workspace:
        raise PermissionDenied("Client company does not belong to this workspace.")

    # 2. Check plan limits
    if status == 'ACTIVE' and not workspace.can_create_job():
        raise PermissionDenied(
            "You have reached the limit of active jobs for your plan. "
            "Please upgrade to Growth or Enterprise to create more."
        )

    # 3. Create the job
    job = JobRequisition.objects.create(
        client_company=client_company,
        title=title,
        description=description,
        ai_parsing_strictness=ai_parsing_strictness,
        status=status,
        category=category
    )
    
    return job
