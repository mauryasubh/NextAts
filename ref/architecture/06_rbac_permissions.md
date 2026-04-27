# Role-Based Access Control (RBAC) Architecture

In an agency setting, maintaining the principle of least privilege is mandatory. An external junior recruiter shouldn't have access to executive compensation details or client billing data.

## Architectural Flow

```mermaid
sequenceDiagram
    participant Requester (Recruiter)
    participant APIGateway as API Gateway
    participant RBAC as Policy Enforcement Point
    participant DB as Database Models

    Requester->>APIGateway: Request: Move Candidate to Hire
    APIGateway->>RBAC: Extract JWT Token (Workspace X, Role: Recruiter)
    
    activate RBAC
    RBAC->>RBAC: Check Role Permissions: Can Recruiter 'Edit_Job_Status'? -> YES
    RBAC->>RBAC: Check Object Level Permission: Is Recruiter assigned to THIS Job? -> YES
    deactivate RBAC

    RBAC-->>APIGateway: Permit Action
    APIGateway->>DB: Execute Update
    DB-->>Requester: 200 OK
```

## Detailed Explanation

The NexATS RBAC system operates dynamically on two intersecting levels:
1. **Vertical Roles:** Global permissions (e.g., `Admin`, `Hiring Manager`, `Interviewer`). An `Interviewer` cannot delete a job. An `Admin` can do anything.
2. **Horizontal Object-Level Permissions:** Even if a user has the `Hiring Manager` role, they might only be explicitly assigned to the `Acme Corp` client branch. If they try to access candidate data for a job listed under `Globex Corp`, the RBAC engine yields a `403 Forbidden` error. This multi-axis security makes the platform enterprise-ready and compliant with data privacy frameworks.
