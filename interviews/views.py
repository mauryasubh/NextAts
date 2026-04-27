import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from .models import Interview
from candidates.models import Application
from users.models import User

@login_required
def calendar_view(request):
    """
    Main calendar page.
    """
    workspace = request.user.workspace
    applications = Application.objects.filter(candidate__workspace=workspace).exclude(stage__in=['HIRED', 'REJECTED'])
    workspace_users = User.objects.filter(workspace=workspace)
    
    return render(request, 'interviews/calendar.html', {
        'applications': applications,
        'workspace_users': workspace_users
    })

@login_required
def api_interviews(request):
    """
    JSON API for FullCalendar.js to fetch events.
    """
    workspace = request.user.workspace
    # Filter by workspace to ensure isolation
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    interviews = Interview.objects.filter(workspace=workspace)
    
    # We can add filtering by date if needed for performance
    events = []
    for interview in interviews:
        events.append({
            'id': str(interview.id),
            'title': f"{interview.application.candidate.first_name}: {interview.title}",
            'start': interview.start_time.isoformat(),
            'end': interview.end_time.isoformat(),
            'extendedProps': {
                'type': interview.interview_type,
                'status': interview.status,
                'candidate': str(interview.application.candidate),
                'job': interview.application.job.title,
                'interviewer': str(interview.interviewer) if interview.interviewer else "Unassigned",
                'location': interview.location_link or ""
            },
            'className': f"status-{interview.status.lower()} type-{interview.interview_type.lower()}"
        })
    
    return JsonResponse(events, safe=False)

@login_required
@csrf_exempt
def api_schedule_interview(request):
    """
    Create a new interview via AJAX.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        
        app_id = data.get('application_id')
        application = get_object_or_404(Application, id=app_id, candidate__workspace=request.user.workspace)
        
        start_time = parse_datetime(data.get('start_time'))
        end_time = parse_datetime(data.get('end_time'))
        
        interviewer_id = data.get('interviewer_id')
        interviewer = None
        if interviewer_id:
            interviewer = User.objects.get(id=interviewer_id, workspace=request.user.workspace)

        interview = Interview.objects.create(
            workspace=request.user.workspace,
            application=application,
            title=data.get('title'),
            interview_type=data.get('interview_type', 'TECHNICAL'),
            interviewer=interviewer,
            start_time=start_time,
            end_time=end_time,
            location_link=data.get('location_link', ''),
            status='SCHEDULED'
        )
        
        # Automatically move application to INTERVIEWING stage
        if application.stage == 'SOURCED':
            application.stage = 'INTERVIEWING'
            application.save()

        return JsonResponse({'status': 'success', 'id': str(interview.id)})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
@csrf_exempt
def api_cancel_interview(request, interview_id):
    """
    Cancel an interview.
    """
    workspace = request.user.workspace
    interview = get_object_or_404(Interview, id=interview_id, workspace=workspace)
    
    if request.method == 'POST':
        interview.status = 'CANCELLED'
        interview.save()
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error'}, status=400)
