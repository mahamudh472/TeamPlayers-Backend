# Agency Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- GET `/api/v1/agency/leads/` — List agency leads, filterable by status, with status counts.
- GET `/api/v1/agency/leads/<id>/` — Retrieve details of a single lead, including its notes.
- POST `/api/v1/agency/leads/<id>/notes/` — Add a new note for a lead.
- PATCH `/api/v1/agency/leads/<id>/status/` — Change a lead's status.
- POST `/api/v1/agency/webhooks/leads/` — Bulk lead ingestion webhook (unauthenticated, secret-verified).
- GET `/api/v1/agency/clients/` — List clients with search, pagination, and static summary metrics.
- POST `/api/v1/agency/clients/` — Create a new client manually.
- GET `/api/v1/agency/clients/<id>/` — Retrieve details of a single client.
- PATCH `/api/v1/agency/clients/<id>/` — Update details of a single client.
- GET `/api/v1/agency/clients/<id>/jobs/` — List active jobs for a specific client.
- GET `/api/v1/agency/clients/<id>/activities/` — List activity history for a specific client.
- GET `/api/v1/agency/clients/<id>/notes/` — List notes for a specific client.
- POST `/api/v1/agency/clients/<id>/notes/` — Add a new note for a specific client.
- GET `/api/v1/agency/jobs/` — List jobs with search, pagination, and static summary metrics.
- POST `/api/v1/agency/jobs/` — Create a new job.
- GET `/api/v1/agency/jobs/<id>/` — Retrieve details of a single job.
- PATCH `/api/v1/agency/jobs/<id>/` — Update details of a single job.

---



## GET /api/v1/agency/leads/

Description: Retrieve all leads belonging to the agency. Results can be filtered by the status query parameter. The response always includes a count of leads grouped by each status.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Query Parameters:
- `status` (Optional) — Filter leads by status choice: `new`, `contacted`, `meeting`, `converted`, `lost`.

Success response (200):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "status_counts": {
    "new": 1,
    "contacted": 0,
    "meeting": 0,
    "converted": 0,
    "lost": 0
  },
  "results": [
    {
      "id": 1,
      "company": "Google",
      "contact_person": "Sundar Pichai",
      "contact_email": "sundar@google.com",
      "contact_phone": "+16502530000",
      "location": "Mountain View, CA",
      "industry": "Technology",
      "source": "Inbound",
      "priority": "high",
      "status": "new",
      "created_at": "2026-06-17T15:23:23.123456Z",
      "updated_at": "2026-06-17T15:23:23.123456Z"
    }
  ]
}
```

Error responses:
- 400: Header missing
```json
{ "detail": "X-Agency-ID header is required" }
```
- 403: Forbidden (User not in agency)
```json
{ "detail": "You do not have permission to access this agency" }
```
- 404: Agency not found
```json
{ "detail": "Agency not found" }
```

---

## GET /api/v1/agency/leads/<id>/

Description: Retrieve detailed information for a single lead, along with a list of notes added to this lead.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "company": "Google",
  "contact_person": "Sundar Pichai",
  "contact_email": "sundar@google.com",
  "contact_phone": "+16502530000",
  "location": "Mountain View, CA",
  "industry": "Technology",
  "source": "Inbound",
  "priority": "high",
  "status": "new",
  "created_at": "2026-06-17T15:23:23.123456Z",
  "updated_at": "2026-06-17T15:23:23.123456Z",
  "notes": [
    {
      "id": 5,
      "content": "Followed up with email to schedule meeting.",
      "model": "lead",
      "model_id": 1,
      "user": {
        "id": "e229d494-b152-4752-95b6-6d2745cf0249",
        "email": "agent@agency.com",
        "full_name": "Agency Agent"
      },
      "created_at": "2026-06-17T15:24:00.123456Z",
      "updated_at": "2026-06-17T15:24:00.123456Z"
    }
  ]
}
```

Error responses:
- 404: Lead not found
```json
{ "detail": "Lead not found" }
```

---

## POST /api/v1/agency/leads/<id>/notes/

Description: Add a new text note for the specified lead.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "content": "Had a quick phone call, positive response."
}
```

Success response (201):

```json
{
  "id": 6,
  "content": "Had a quick phone call, positive response.",
  "model": "lead",
  "model_id": 1,
  "user": {
    "id": "e229d494-b152-4752-95b6-6d2745cf0249",
    "email": "agent@agency.com",
    "full_name": "Agency Agent"
  },
  "created_at": "2026-06-17T15:25:30.123456Z",
  "updated_at": "2026-06-17T15:25:30.123456Z"
}
```

Error responses:
- 400: Content missing or empty
```json
{ "error": "content is required and cannot be empty" }
```
- 404: Lead not found
```json
{ "detail": "Lead not found" }
```

---

## POST /api/v1/agency/webhooks/leads/

Description: Ingest one or more leads in JSON format from external services. Validates the global secret from settings and associates the leads with the specified agency.

Auth: Not required (Public URL, validated via `secret` payload field)

Request JSON:

```json
{
  "agency_id": 1,
  "secret": "your_leads_webhook_secret_key",
  "leads": [
    {
      "company": "Partner Company A",
      "contact_person": "Jane Partner",
      "contact_email": "jane@partner.com",
      "contact_phone": "+15550199",
      "location": "San Francisco, CA",
      "industry": "Finance",
      "source": "Partner Portal",
      "priority": "medium",
      "status": "new"
    }
  ]
}
```

Success response (201):

```json
{
  "message": "Successfully created 1 leads",
  "created_leads": [
    {
      "id": 15,
      "company": "Partner Company A",
      "contact_person": "Jane Partner",
      "contact_email": "jane@partner.com",
      "contact_phone": "+15550199",
      "location": "San Francisco, CA",
      "industry": "Finance",
      "source": "Partner Portal",
      "priority": "medium",
      "status": "new",
      "created_at": "2026-06-17T16:10:00.123456Z",
      "updated_at": "2026-06-17T16:10:00.123456Z"
    }
  ]
}
```

Error responses:

- 400: Required fields missing or invalid leads list format
```json
{
  "detail": "leads must be a non-empty list"
}
```

- 400: Validation error on specific lead fields
```json
{
  "detail": "Validation failed for one or more leads",
  "errors": [
    {
      "company": ["This field is required."]
    }
  ]
}
```

- 401: Invalid secret
```json
{
  "detail": "Invalid or missing webhook secret"
}
```

- 404: Agency not found
```json
{
  "detail": "Agency not found"
}
```

---

## PATCH /api/v1/agency/leads/<id>/status/

Description: Update the status of a specific lead belonging to the agency.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "status": "contacted"
}
```

Success response (200):

```json
{
  "id": 1,
  "company": "Google",
  "contact_person": "Sundar Pichai",
  "contact_email": "sundar@google.com",
  "contact_phone": "+16502530000",
  "location": "Mountain View, CA",
  "industry": "Technology",
  "source": "Inbound",
  "priority": "high",
  "status": "contacted",
  "created_at": "2026-06-17T15:23:23.123456Z",
  "updated_at": "2026-06-17T16:35:00.123456Z"
}
```

Error responses:

- 400: Status parameter missing
```json
{
  "error": "status is required"
}
```

- 400: Invalid status choice
```json
{
  "detail": "Invalid status choice. Must be one of: new, contacted, meeting, converted, lost"
}
```

- 404: Lead not found
```json
{
  "detail": "Lead not found"
}
```


---

## GET /api/v1/agency/clients/

Description: Retrieve all clients belonging to the agency. Results can be paginated and filtered using the `search` query parameter. The search matches against company, contact person, contact email, location, industry, or contact phone. Also includes static summary metrics: `active_clients`, `total_revenue`, and `placement_rate`.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Query Parameters:
- `search` (Optional) — Filter clients by a search term.
- `page` (Optional) — Page number.
- `page_size` (Optional) — Page size limit.

Success response (200):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "active_clients": 12,
  "total_revenue": 45000.0,
  "placement_rate": 85.5,
  "results": [
    {
      "id": 1,
      "lead": 5,
      "company": "Acme Corp",
      "contact_person": "John Doe",
      "contact_email": "john.doe@acme.com",
      "contact_phone": "+15550100",
      "location": "New York, NY",
      "industry": "Manufacturing",
      "is_active": true,
      "jobs": 3,
      "placements": 2,
      "revenue": 15000.0,
      "created_at": "2026-06-18T10:00:00.123456Z",
      "updated_at": "2026-06-18T10:00:00.123456Z"
    }
  ]
}
```

Error responses:
- 400: Header missing
```json
{ "detail": "X-Agency-ID header is required" }
```
- 403: Forbidden (User not in agency)
```json
{ "detail": "You do not have permission to access this agency" }
```

---

## POST /api/v1/agency/clients/

Description: Manually create a new client for the agency. The client does not reference any existing Lead.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "company": "Innovative Labs",
  "contact_person": "Alice Smith",
  "contact_email": "alice@innovativelabs.com",
  "contact_phone": "+15550220",
  "location": "Boston, MA",
  "industry": "Biotech",
  "is_active": true,
  "note": "Initial introductory meeting went very well."
}
```

Success response (201):

```json
{
  "message": "Client created successfully"
}
```

Error responses:
- 400: Validation error (e.g. missing required field `company`)
```json
{
  "company": [
    "This field is required."
  ]
}
```

---

## GET /api/v1/agency/clients/<id>/

Description: Retrieve details of a single client.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "lead": 5,
  "company": "Acme Corp",
  "contact_person": "John Doe",
  "contact_email": "john.doe@acme.com",
  "contact_phone": "+15550100",
  "location": "New York, NY",
  "industry": "Manufacturing",
  "is_active": true,
  "jobs": 3,
  "placements": 2,
  "revenue": 15000.0,
  "success_rate": 92.5,
  "last_ai_summary": {
    "id": 1,
    "summary": "This client has strong hiring trends but some risk of role cancellations.",
    "collabration_strength": ["high", "medium"],
    "risks": ["role cancellation"],
    "created_at": "2026-06-18T11:00:00.123456Z",
    "updated_at": "2026-06-18T11:00:00.123456Z"
  },
  "client_health": "healthy",
  "hiring_success_rate": 88.0,
  "recommended_actions": [
    "Schedule quarterly review meeting",
    "Follow up on pending candidate interviews",
    "Send renewal proposal for the technical consulting contract"
  ],
  "created_at": "2026-06-18T10:00:00.123456Z",
  "updated_at": "2026-06-18T10:00:00.123456Z"
}
```

Error responses:
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## PATCH /api/v1/agency/clients/<id>/

Description: Update detailed information for a single client. The `note` field is excluded and not allowed on client updates.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "contact_person": "Jane Doe",
  "contact_email": "jane.doe@acme.com"
}
```

Success response (200):

```json
{
  "message": "Client updated successfully"
}
```

Error responses:
- 400: Validation error (e.g. attempting to update the note field)
```json
{
  "note": [
    "The note field is not allowed on client update."
  ]
}
```
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## GET /api/v1/agency/clients/<id>/jobs/

Description: Retrieve active jobs for a specific client. By default, it returns jobs where `status='open'` (active) to populate the "Active Jobs" UI section. The results can be customized to include all jobs or jobs of other statuses using the `status` query parameter.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Query Parameters:
- `status` (Optional) — Filter jobs by status choices: `open`, `closed`, `filled`, or `all` to disable status filtering. Default is `open`.

Success response (200):

```json
[
  {
    "id": 1,
    "client": 2,
    "client_name": "Innovative Labs",
    "title": "Senior Software Engineer",
    "description": "Develop and maintain robust web services and integrations.",
    "location": "London, UK",
    "salary_range": "£70,000 - £90,000",
    "experince_required": 5,
    "skills": ["Python", "Django", "PostgreSQL"],
    "job_type": "remote",
    "status": "open",
    "description_file": null,
    "applicants": 45,
    "shortlisted": 8,
    "interviewed": 2,
    "created_at": "2026-06-18T12:00:00.123456Z",
    "updated_at": "2026-06-18T12:00:00.123456Z"
  },
  {
    "id": 2,
    "client": 2,
    "client_name": "Innovative Labs",
    "title": "Product Manager",
    "description": "Manage the lifecycle of technical products and lead scrum teams.",
    "location": "Manchester, UK",
    "salary_range": "£60,000 - £80,000",
    "experince_required": 3,
    "skills": ["Agile", "Scrum", "Product Backlog"],
    "job_type": "hybrid",
    "status": "open",
    "description_file": null,
    "applicants": 32,
    "shortlisted": 6,
    "interviewed": 1,
    "created_at": "2026-06-18T12:30:00.123456Z",
    "updated_at": "2026-06-18T12:30:00.123456Z"
  }
]
```

Error responses:
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## GET /api/v1/agency/clients/<id>/activities/

Description: Retrieve a history of activities associated with a specific client.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
[
  {
    "id": 1,
    "client": 2,
    "user": {
      "id": "e229d494-b152-4752-95b6-6d2745cf0249",
      "email": "agent@agency.com",
      "full_name": "Agency Agent"
    },
    "summary": "Sent a follow-up email about candidate resumes",
    "created_at": "2026-06-19T09:00:00.123456Z",
    "updated_at": "2026-06-19T09:00:00.123456Z"
  }
]
```

Error responses:
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## GET /api/v1/agency/clients/<id>/notes/

Description: Retrieve all notes associated with a specific client, ordered newest first.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
[
  {
    "id": 12,
    "content": "Requested updated pricing for contracting roles.",
    "model": "client",
    "model_id": 2,
    "user": {
      "id": "e229d494-b152-4752-95b6-6d2745cf0249",
      "email": "agent@agency.com",
      "full_name": "Agency Agent"
    },
    "created_at": "2026-06-19T08:30:00.123456Z",
    "updated_at": "2026-06-19T08:30:00.123456Z"
  }
]
```

Error responses:
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## POST /api/v1/agency/clients/<id>/notes/

Description: Add a new text note for a specific client.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "content": "Had a status update call, client is happy with candidates."
}
```

Success response (201):

```json
{
  "id": 13,
  "content": "Had a status update call, client is happy with candidates.",
  "model": "client",
  "model_id": 2,
  "user": {
    "id": "e229d494-b152-4752-95b6-6d2745cf0249",
    "email": "agent@agency.com",
    "full_name": "Agency Agent"
  },
  "created_at": "2026-06-19T10:50:00.123456Z",
  "updated_at": "2026-06-19T10:50:00.123456Z"
}
```

Error responses:
- 400: Content missing or empty
```json
{ "error": "content is required and cannot be empty" }
```
- 404: Client not found
```json
{ "detail": "Client not found" }
```

---

## GET /api/v1/agency/jobs/

Description: Retrieve all jobs belonging to the agency. Results can be paginated and filtered using the `search` query parameter. The search matches against title, description, location, or client company. Includes static summary metrics: `active_jobs`, `total_applicants`, `shortlisted`, and `avg_time_to_fill`. Each list item also includes static `applicants`, `shortlisted`, and `interviewed` metrics.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Query Parameters:
- `search` (Optional) — Filter jobs by a search term.
- `page` (Optional) — Page number.
- `page_size` (Optional) — Page size limit.

Success response (200):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "active_jobs": 8,
  "total_applicants": 42,
  "shortlisted": 15,
  "avg_time_to_fill": 18.5,
  "results": [
    {
      "id": 1,
      "client": 2,
      "client_name": "Innovative Labs",
      "title": "Senior Python Developer",
      "description": "Develop and maintain robust web services and integrations.",
      "location": "Boston, MA",
      "salary_range": "$110k - $130k",
      "experince_required": 5,
      "skills": ["Python", "Django", "PostgreSQL"],
      "job_type": "remote",
      "status": "open",
      "description_file": null,
      "applicants": 12,
      "shortlisted": 4,
      "interviewed": 2,
      "created_at": "2026-06-18T12:00:00.123456Z",
      "updated_at": "2026-06-18T12:00:00.123456Z"
    }
  ]
}
```

Error responses:
- 400: Header missing
```json
{ "detail": "X-Agency-ID header is required" }
```
- 403: Forbidden (User not in agency)
```json
{ "detail": "You do not have permission to access this agency" }
```

---

## POST /api/v1/agency/jobs/

Description: Create a new job associated with the agency and client.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "client": 2,
  "title": "Senior Python Developer",
  "description": "Develop and maintain robust web services and integrations.",
  "location": "Boston, MA",
  "salary_range": "$110k - $130k",
  "experince_required": 5,
  "skills": ["Python", "Django", "PostgreSQL"],
  "job_type": "remote",
  "status": "open"
}
```

Success response (201):

```json
{
  "id": 1,
  "client": 2,
  "client_name": "Innovative Labs",
  "title": "Senior Python Developer",
  "description": "Develop and maintain robust web services and integrations.",
  "location": "Boston, MA",
  "salary_range": "$110k - $130k",
  "experince_required": 5,
  "skills": ["Python", "Django", "PostgreSQL"],
  "job_type": "remote",
  "status": "open",
  "description_file": null,
  "applicants": 12,
  "shortlisted": 4,
  "interviewed": 2,
  "created_at": "2026-06-18T12:00:00.123456Z",
  "updated_at": "2026-06-18T12:00:00.123456Z"
}
```

Error responses:
- 400: Validation error (e.g. client does not belong to the agency)
```json
{
  "client": [
    "Client does not belong to this agency."
  ]
}
```

---

## GET /api/v1/agency/jobs/<id>/

Description: Retrieve details of a single job.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "client": 2,
  "client_name": "Innovative Labs",
  "title": "Senior Python Developer",
  "description": "Develop and maintain robust web services and integrations.",
  "location": "Boston, MA",
  "salary_range": "$110k - $130k",
  "experince_required": 5,
  "skills": ["Python", "Django", "PostgreSQL"],
  "job_type": "remote",
  "status": "open",
  "description_file": null,
  "applicants": 12,
  "shortlisted": 4,
  "interviewed": 2,
  "created_at": "2026-06-18T12:00:00.123456Z",
  "updated_at": "2026-06-18T12:00:00.123456Z"
}
```

Error responses:
- 404: Job not found
```json
{ "detail": "Job not found" }
```

---

## PATCH /api/v1/agency/jobs/<id>/

Description: Partially update details of a single job.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "status": "closed"
}
```

Success response (200):

```json
{
  "id": 1,
  "client": 2,
  "client_name": "Innovative Labs",
  "title": "Senior Python Developer",
  "description": "Develop and maintain robust web services and integrations.",
  "location": "Boston, MA",
  "salary_range": "$110k - $130k",
  "experince_required": 5,
  "skills": ["Python", "Django", "PostgreSQL"],
  "job_type": "remote",
  "status": "closed",
  "description_file": null,
  "applicants": 12,
  "shortlisted": 4,
  "interviewed": 2,
  "created_at": "2026-06-18T12:00:00.123456Z",
  "updated_at": "2026-06-18T12:07:00.123456Z"
}
```

Error responses:
- 404: Job not found
```json
{ "detail": "Job not found" }
```




