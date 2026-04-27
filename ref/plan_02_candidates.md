# Feature 2: Candidates & Processing Module

## Overview
The Candidates module manages people entering the pipeline. It focuses intensely on the "AI-Native" aspect of the ATS by automatically parsing resumes and scoring applicants upon entry instead of forcing manual data entry.

## Business Logic & Constraints
- **AI Worker Integration**: In the future (Phase 3), the act of creating a candidate will trigger background Celery tasks that run OCR or LLM operations on uploaded resumes. For this phase, we map out the interface that hooks into that structure.
- **Workflow State**: Candidates must have a defined state (`SOURCED`, `INTERVIEWING`, `OFFERED`, `REJECTED`) tied directly to a specific `JobRequisition`.

## User Workflow

### 1. Global Candidate Directory (`/candidates/`)
- A master list of every candidate the workspace has ever interacted with, regardless of which job they applied to.
- Features powerful, fast searching across Names, Tags, and AI Scores.

### 2. Candidate Ingestion (`/candidates/new/` or via API)
- The user uploads a Resume PDF and selects which `JobRequisition` the candidate is applying for.
- *Magic Moment*: Submitting the form immediately routes the document to the background processor (mocked for now, Celery later), extracts their Name, Email, and Skills, and generates a unified Candidate Profile.

### 3. Pipeline Movement (Kanban Drag & Drop)
- Inside the Job Detail view (from Feature 1), Candidates appear as cards.
- The user intuitively clicks or uses a dropdown (or drag and drop if implemented via AlpineJS/HTMX later) to change a candidate's status.
- Example: Changing status from `SOURCED` to `INTERVIEWING` automatically saves the candidate's new state in the database.

### 4. Detailed Candidate View (`/candidates/<id>/`)
- Clicking a candidate reveals their full profile on a beautifully styled slide-out or full page.
- Displays the original resume side-by-side with the AI-extracted "Pros & Cons" and their overall Compatibility Score.

## Technical Architecture Needed
- **Models**: `Candidate` (General info: Name, Email, Resume File) and `JobApplication` (Mapping table: Linking Candidate -> Job with specific Status and Score).
- **Views**: 
  - `CandidateDirectoryView`: Master search list.
  - `CandidateCreateView`: Handles the file upload and initiates processing workflow.
  - `ApplicationUpdateAPI`: A minor API or POST endpoint to handle updating a candidate's pipeline status quickly.
- **Tools**: Django File Storage for resumes.
