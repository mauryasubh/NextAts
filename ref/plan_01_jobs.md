# Feature 1: Jobs Module

## Overview
The Jobs module allows hiring teams to create, edit, and manage active job requisitions. It acts as the backbone of the platform since candidates and interviews are strictly tied to specific Jobs. 

## Business Logic & Constraints
- **Subscription Enforced**: The system must enforce the "Starter (Free) Plan" limit of maximum 2 *Active* Jobs at any given time per Workspace. 
- **AI-Native Context**: Every job needs specific fields designating "Required Skills" and "AI Screening Criteria" so the system knows what to parse candidate resumes against later.

## User Workflow

### 1. Job Listing Interface (`/jobs/`)
- A beautiful data table or grid displaying all current job requisitions.
- Shows metrics per job (e.g., Total Candidates Sourced, Candidates in Interview, Job Status: Active/Closed).
- Contains a prominent "Create New Job" button.

### 2. Job Creation Flow (`/jobs/new/`)
- Clicking "Create New Job" first runs through a middleware/service check: *If the user is on the Starter Plan and already has 2 Active Jobs, redirect with an error message and prompt an upgrade.*
- Presents a visually crisp form to enter Job Title, Location, Salary Range, Description, and AI Sourcing Keywords.
- Submitting the form saves the `JobRequisition` tied natively to their `Workspace`.

### 3. Job Details View (`/jobs/<id>/`)
- Clicking a specific job opens a detailed Kanban-style pipeline isolated *just* for that job (Sourced -> Phone Screen -> Interview -> Offer).
- Acts as the central hub for recruiters to filter out the noise and only look at the talent pool for this specific role.

## Technical Architecture Needed
- **Models**: We already sketched `JobRequisition` in `jobs/models.py`. Needs verification that fields match the flow.
- **Views**: 
  - `JobListView`: Renders the grid of jobs.
  - `JobCreateView`: Renders form, handles POST, executes limit checks via our service layer.
  - `JobDetailView`: Renders the Kanban pipeline for a specific job.
- **Templates**: `jobs/list.html`, `jobs/create.html`, `jobs/detail.html`.
