# Candidate Ingestion & AI Parsing Workflow

This is the most compute-heavy and complex workflow in NexATS. It dictates how raw PDFs/documents submitted by candidates are systematically transformed into actionable, scored datasets within the database.

## Architectural Flow

```mermaid
sequenceDiagram
    participant Candidate
    participant UploadAPI as Ingestion API
    participant ObjectStore as S3/R2 Storage
    participant Celery as Celery Task Queue
    participant AIEngine as Vector AI Parsing Engine
    participant GlobalDB as Talent Pool DB
    participant AppDB as Specific Job Application DB

    Candidate->>UploadAPI: Submits Resume (PDF) + Details
    UploadAPI->>ObjectStore: Save Raw PDF Document
    ObjectStore-->>UploadAPI: Return CDN / Storage URL
    
    UploadAPI->>Celery: Async: Dispatch Resume Analysis Task
    UploadAPI-->>Candidate: Return 200 OK (Application Received)
    
    activate Celery
    Celery->>AIEngine: Send Document bytes for Extraction
    AIEngine->>AIEngine: OCR, Semantic Extraction, Skill Vectorization
    AIEngine-->>Celery: Return Structured JSON (Experience, Skills, Meta)
    
    Celery->>GlobalDB: Upsert / Create global Candidate Profile (John Smith)
    Celery->>AppDB: Create Application linking Candidate <-> Job
    
    Celery->>AIEngine: Evaluate Structured Profile against Job AI Strictness Rules
    AIEngine-->>Celery: Return Match Score (e.g. 98%)
    
    Celery->>AppDB: Commit Match Score to Application Record
    deactivate Celery
```

## Detailed Explanation

1. **Decoupled Uploads:** When a candidate uploads a resume, the system must not block or freeze waiting for the AI. The document is immediately dumped to a Cloud Storage bucket, and a rapid acknowledgment is sent to the candidate.
2. **Asynchronous Processing (Celery):** The ATS relies on a robust Celery worker queue. The heavy lifting is handed off via a background task. 
3. **AI Extraction Phase:** The engine parses the PDF, ignoring formatting biases, and extracting raw chronological facts, educational history, and implicit skill vectors using Natural Language Processing.
4. **Global Talent Creation:** The extracted data is constructed into an agnostic Candidate JSON profile, which gets cached in the Global Talent Pool database for the agency.
5. **Conditional Scoring:** Finally, the structured candidate profile is mathematically compared against the specific ruleset configured in the `Job Requisition`. A strict match score is plotted and permanently assigned to their active `Application` record, immediately slotting them into the recruiter's Kanban board.
