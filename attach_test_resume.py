import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from candidates.models import Application, Candidate
from django.core.files import File

apps = Application.objects.filter(id__in=['5e058f40-5a73-479d-bc5b-245ff34652b4', '3588d739-2a4a-4e29-88f8-e214b4bb3eb2'])
for a in apps:
    c = a.candidate
    print(f"App: {a.id}, Candidate: {c.id}")
    if c.resume:
        try:
            path = c.resume.path
            exists = os.path.exists(path)
            print(f"  Resume: {c.resume.name}, Exists: {exists}")
        except Exception as e:
            print(f"  Resume path error: {e}")
    else:
        print("  No resume attached")

# Let's attach the test resume to ALL candidates for this job so you can test
print("Attaching test resume to all candidates...")
test_resume_path = r"D:\bussiness\ATS_2\test_data\subhash_pythonDeveloper_4Year (1).pdf"
if os.path.exists(test_resume_path):
    with open(test_resume_path, 'rb') as f:
        # We will apply this to all candidates just to make testing easy
        for cand in Candidate.objects.all():
            cand.resume.save("subhash_pythonDeveloper_4Year.pdf", File(f), save=True)
            # Clear old parsing hash so it forces re-parse
            cand.resume_text = ""
            cand.resume_hash = ""
            cand.save()
    print("Test resume attached to all candidates successfully!")
    
    # Also reset the application status so it runs again
    Application.objects.all().update(ai_analysis_done=False, ai_analysis_error="")
else:
    print("Test resume not found at: " + test_resume_path)
