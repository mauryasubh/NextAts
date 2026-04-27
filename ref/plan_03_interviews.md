# Feature 3: Interviews & Scheduling Module

## Overview
The Interviews module is the action-center where Candidates actively engaged in a pipeline are scheduled to converse with the Team. It shifts the ATS from an asynchronous file-cabinet into a real-time scheduling tool.

## Business Logic & Constraints
- **State Requirement**: An interview can only be created for a candidate currently linked to a Job (i.e. an active `JobApplication`). 
- **Time Sensitivity**: The dashboard must query upcoming interviews (e.g., Interviews occurring today/tomorrow) for quick visibility.

## User Workflow

### 1. Unified Calendar/List View (`/interviews/`)
- A specialized screen displaying all upcoming and past interviews across the workspace.
- Chronologically ordered so the user knows exactly who they are talking to today.

### 2. Interview Creation (Modal or `/interviews/new/`)
- Often accessed directly from a Candidate's Profile card.
- User selects the Candidate, inputs a Date, Time, and Interview Type (e.g., Phone Screen vs. Technical Panel).
- Saves the `Interview` object tied to the `JobApplication`.

### 3. Interview Activity Logging
- After an interview concludes, the recruiter can drop a "Score" or "Notes" on the interview object.
- Completing the interview often acts as a trigger to either move the candidate to `OFFERED` or `REJECTED` in the pipeline.

## Technical Architecture Needed
- **Models**: `Interview` (Requires linking to the specific `JobApplication`, containing `scheduled_time`, `duration`, `interview_type`, and `notes`).
- **Views**: 
  - `InterviewAgendaView`: Pulls `Interview.objects.filter(application__job__workspace=user.workspace).order_by('scheduled_time')`.
  - `InterviewCreateAPI`: A view handling POST data to spawn an interview.
- **Dashboard Hooks**: We will need to write a quick selector in our domain logic (e.g., `get_upcoming_interviews_for_workspace`) to populate the `Upcoming Interviews` widget on the main dashboard screen we just finished!
