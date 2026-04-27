# Automated Tenant & Team Provisioning Workflow

The Tenant Provisioning workflow is the foundational entry point into NexATS. Because all data is heavily partitioned by workspaces, setting up the tenant correctly is required before any hiring can occur.

## Architectural Flow

```mermaid
sequenceDiagram
    participant User
    participant AuthSystem as Auth Service
    participant TenantDB as Tenant Manager
    participant RoleSystem as RBAC System
    participant Email as Notification Queue

    User->>AuthSystem: Submits Signup Form (Agency Name, Email, Password)
    AuthSystem->>TenantDB: Request Workspace Allocation
    
    activate TenantDB
    TenantDB->>TenantDB: Create strict `Workspace` Entity
    TenantDB->>TenantDB: Create `CustomUser` Entity
    TenantDB->>RoleSystem: Bind `CustomUser` to `Workspace` as Owner
    deactivate TenantDB
    
    TenantDB->>Email: Trigger 'Tenant Ready' Asynchronous task
    Email-->>User: Dispatch Verification & Welcome Email

    User->>AuthSystem: Login Request
    AuthSystem-->>User: JWT Token / Session Cookie with `workspace_id` claim
    
    note right of User: User can now invite other Team Members
    User->>RoleSystem: Invite Recruiter (Email)
    RoleSystem->>Email: Dispatch Invitation Link
```

## Detailed Explanation

1. **Origin of Isolation (The Workspace):** When an agency initially signs up, the very first database query creates a `Workspace` record. This guarantees that an isolated logical bucket exists.
2. **Owner Binding:** The user is generated and explicitly given the "Owner" flag within the Role-Based Access Control (RBAC) component, and hard-linked to the new `workspace_id`.
3. **Session Awareness:** When this user logs in, their session or token natively encrypts the `workspace_id`. Every single subsequent database query in the ATS automatically intercepts this token and pre-filters `WHERE workspace_id = X`.
4. **Team Invites:** The owner can utilize their permissions to generate invites for other "Team Members" (e.g., specific headhunters or recruiters). Because the Owner generated the invite, the invited users are automatically bound to the exact same partition space when they register.
