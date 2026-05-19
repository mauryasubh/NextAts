import logging
import re
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import F

logger = logging.getLogger(__name__)

def update_task_tracker(task_tracker_id: str, is_success: bool):
    """Helper to update JobAnalysisTask progress and check for completion."""
    if not task_tracker_id:
        return
        
    from jobs.models import JobAnalysisTask
    try:
        tracker = JobAnalysisTask.objects.get(id=task_tracker_id)
        if is_success:
            tracker.processed_profiles = F('processed_profiles') + 1
            tracker.save(update_fields=['processed_profiles'])
        else:
            tracker.failed_profiles = F('failed_profiles') + 1
            tracker.save(update_fields=['failed_profiles'])
            
        tracker.refresh_from_db()
        if tracker.processed_profiles + tracker.failed_profiles >= tracker.total_profiles:
            tracker.status = 'COMPLETED'
            tracker.completed_at = timezone.now()
            tracker.save(update_fields=['status', 'completed_at'])
    except JobAnalysisTask.DoesNotExist:
        pass

@shared_task(bind=True, max_retries=3)
def analyze_single_application(self, application_id: str, task_tracker_id: str = None):
    """Analyze one candidate's resume against their job."""
    from candidates.models import Application
    from candidates.services.resume_parser import extract_resume_text
    from jobs.services.ai_analyzer import analyze_candidate_for_job
    
    try:
        app = Application.objects.select_related('candidate', 'job').get(id=application_id)
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found.")
        return {'status': 'error', 'reason': 'Application not found'}
    
    # Skip if already analyzed
    if app.ai_analysis_done:
        return {'status': 'skipped', 'reason': 'Already analyzed'}
        
    app.ai_analysis_started_at = timezone.now()
    app.save(update_fields=['ai_analysis_started_at'])
    
    try:
        candidate = app.candidate
        
        # 1. Extract resume text (this handles caching natively)
        updated, resume_text = extract_resume_text(candidate)
        
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text is empty or missing")
            
        # Clean up and truncate by word count to avoid mid-word slicing
        cleaned_resume = re.sub(r'\s+', ' ', resume_text).strip()
        words = cleaned_resume.split(' ')
        truncated_resume = ' '.join(words[:3000]) # Roughly 4000 tokens, well within limits
        
        # 2. Run LLM analysis
        # Use condensed requirements if available to save tokens
        job_description = app.job.ai_condensed_requirements or app.job.description
        
        result = analyze_candidate_for_job(
            job_description=job_description,
            resume_text=truncated_resume,  
            strictness=app.job.ai_parsing_strictness
        )
        
        # 3. Save results
        app.ai_match_score = result.get('overall_score', 0)
        app.ai_skills_score = result.get('skills_score', 0)
        app.ai_experience_score = result.get('experience_score', 0)
        app.ai_culture_score = result.get('culture_score', 0)
        app.ai_resume_score = result.get('resume_score', 0)
        app.ai_matched_skills = result.get('matched_skills', [])
        app.ai_missing_skills = result.get('missing_skills', [])
        app.ai_strengths = result.get('strengths', [])
        app.ai_gaps = result.get('gaps', [])
        app.ai_recommendation = result.get('recommendation', 'Review')
        app.ai_experience_years = result.get('experience_years', 0)
        app.ai_culture_fit = result.get('culture_fit', 'Medium')
        app.ai_summary = result.get('summary', '')
        
        app.ai_analysis_done = True
        app.ai_analysis_completed_at = timezone.now()
        app.ai_analysis_error = None
        app.save()
        
        # Update tracker
        update_task_tracker(task_tracker_id, is_success=True)
        
        return {'status': 'success', 'application_id': str(app.id)}
        
    except Exception as exc:
        logger.exception(f"Error analyzing application {application_id}: {exc}")
        app.ai_analysis_error = str(exc)
        app.save(update_fields=['ai_analysis_error'])
        
        if self.request.retries >= self.max_retries:
            # Exhausted all retries
            update_task_tracker(task_tracker_id, is_success=False)
            raise exc
        else:
            # Retry with exponential backoff (starts at 30s)
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task(bind=True)
def analyze_job_candidates(self, job_id: str, task_tracker_id: str):
    """Master task: Dispatch analysis for all pending candidates in a job."""
    from candidates.models import Application
    from jobs.models import JobAnalysisTask
    
    try:
        tracker = JobAnalysisTask.objects.select_related('job').get(id=task_tracker_id)
    except JobAnalysisTask.DoesNotExist:
        logger.error(f"JobAnalysisTask {task_tracker_id} not found.")
        return
        
    tracker.status = 'PROCESSING'
    tracker.started_at = timezone.now()
    tracker.save(update_fields=['status', 'started_at'])
    
    # Pre-process the Job Description to save tokens for individual candidate analysis
    job = tracker.job
    if not job.ai_condensed_requirements:
        from jobs.services.ai_analyzer import extract_job_requirements
        job.ai_condensed_requirements = extract_job_requirements(job.description)
        job.save(update_fields=['ai_condensed_requirements'])
    
    # We only want to analyze candidates that haven't been analyzed yet
    # AND that actually have a resume uploaded
    pending_apps = Application.objects.filter(
        job_id=job_id,
        ai_analysis_done=False,
        candidate__resume__isnull=False,  
    ).exclude(candidate__resume='')
    
    total = pending_apps.count()
    tracker.total_profiles = total
    tracker.save(update_fields=['total_profiles'])
    
    if total == 0:
        tracker.status = 'COMPLETED'
        tracker.completed_at = timezone.now()
        tracker.save(update_fields=['status', 'completed_at'])
        return {'status': 'success', 'message': 'No pending profiles'}
        
    # Dispatch individual tasks asynchronously
    for app in pending_apps:
        try:
            analyze_single_application.delay(str(app.id), task_tracker_id=task_tracker_id)
        except Exception as e:
            logger.error(f"Failed to dispatch task for app {app.id}: {e}")
            from django.db.models import F
            tracker.failed_profiles = F('failed_profiles') + 1
            tracker.save(update_fields=['failed_profiles'])
            
    # Polling the DB for completion state is better handled 
    # via the frontend calling a status endpoint or a periodic task, 
    # instead of blocking this worker.
    return {'status': 'dispatched', 'total_dispatched': total}
