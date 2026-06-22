# Agency Candidates Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

## Endpoint Inventory

- GET `/api/v1/agency/candidates/` — List candidates with search, pagination, and status counts.
- GET `/api/v1/agency/candidates/<id>/` — Retrieve details of a single candidate.
- GET `/api/v1/agency/candidates/<id>/notes/` — Retrieve notes for a single candidate.
- POST `/api/v1/agency/candidates/<id>/notes/` — Add a note for a single candidate.
- POST `/api/v1/agency/candidates/<id>/shortlist/` — Shortlist a candidate.
- POST `/api/v1/agency/candidates/<id>/meeting/` — Create Zoom meeting and invite candidate.
- POST `/api/v1/agency/candidates/<id>/offer/` — Send offer and create placement.
- POST `/api/v1/agency/candidates/<id>/accept/` — Set candidate status to accepted.
- POST `/api/v1/agency/candidates/<id>/reject/` — Set candidate status to rejected.

---

## GET /api/v1/agency/candidates/

Description: Retrieve all candidates belonging to the agency. Results can be paginated and filtered using the `search` query parameter. The search matches against name, email, location, or job title. Includes candidate metrics: `total_candidates`, `shortlisted`, `interviewing`, and `rejected`.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Query Parameters:
- `search` (Optional) — Filter candidates by a search term.
- `page` (Optional) — Page number.
- `page_size` (Optional) — Page size limit.

Success response (200):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "total_candidates": 1,
  "shortlisted": 0,
  "interviewing": 0,
  "rejected": 0,
  "results": [
    {
      "id": 1,
      "name": "Jane Smith",
      "job_name": "Senior Software Engineer",
      "location": "San Francisco, CA",
      "experience": 5,
      "current_salary": "$120,000",
      "expected_salary": "$140,000",
      "applied": "2026-06-20T10:00:00.123456Z",
      "overall_match_percentage": 85.0
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

## GET /api/v1/agency/candidates/<id>/

Description: Retrieve details of a single candidate, including AI match breakdown, job info, and recommended actions.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "+15550199",
  "location": "San Francisco, CA",
  "experience": 5,
  "skills": ["Python", "Django", "React"],
  "current_salary": "$120,000",
  "expected_salary": "$140,000",
  "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
  "status": "new",
  "applied": "2026-06-20T10:00:00.123456Z",
  "applied_at": "2026-06-20T10:00:00.123456Z",
  "ai_analysis": {
    "summary": "Strong candidate with solid backend and frontend experience.",
    "key_strength": ["Django proficiency", "System design"],
    "potential_concerns": ["Expected salary is slightly high"],
    "skills_match": 90.0,
    "experience_match": 85.0,
    "salary_match": 80.0,
    "location_match": 100.0,
    "overall_match_percentage": 85.0
  },
  "job_info": {
    "id": 2,
    "name": "Senior Software Engineer",
    "location": "San Francisco, CA",
    "salary_range": "$110,000 - $130,000"
  },
  "recommended_actions": [
    "Schedule next round interview",
    "Request reference checks from candidate",
    "Send technical assessment test",
    "Review portfolio and key projects"
  ]
}
```

Error responses:
- 404: Candidate not found
```json
{ "detail": "Candidate not found" }
```

---

## GET /api/v1/agency/candidates/<id>/notes/

Description: Retrieve all notes associated with a specific candidate, ordered newest first.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
[
  {
    "id": 1,
    "content": "Candidate requested to reschedule interview to Friday.",
    "model": "candidate",
    "model_id": 1,
    "user": {
      "id": 2,
      "email": "agent@agency.com",
      "full_name": "Agency Agent"
    },
    "created_at": "2026-06-20T10:05:00.123456Z",
    "updated_at": "2026-06-20T10:05:00.123456Z"
  }
]
```

Error responses:
- 404: Candidate not found
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/notes/

Description: Add a new text note for a specific candidate.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "content": "Discussed details over phone, candidate seems very interested."
}
```

Success response (201):

```json
{
  "id": 2,
  "content": "Discussed details over phone, candidate seems very interested.",
  "model": "candidate",
  "model_id": 1,
  "user": {
    "id": 2,
    "email": "agent@agency.com",
    "full_name": "Agency Agent"
  },
  "created_at": "2026-06-20T10:10:00.123456Z",
  "updated_at": "2026-06-20T10:10:00.123456Z"
}
```

Error responses:
- 400: Content missing or empty
```json
{ "error": "content is required and cannot be empty" }
```
- 404: Candidate not found
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/shortlist/

Description: Shortlists a candidate (transitions status from `new` to `shortlisted`).

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "+15550199",
  "location": "San Francisco, CA",
  "experience": 5,
  "skills": ["Python", "Django", "React"],
  "current_salary": "$120,000",
  "expected_salary": "$140,000",
  "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
  "status": "shortlisted",
  "applied": "2026-06-20T10:00:00.123456Z",
  "applied_at": "2026-06-20T10:00:00.123456Z",
  "ai_analysis": {
    "summary": "Strong candidate with solid backend and frontend experience.",
    "key_strength": ["Django proficiency", "System design"],
    "potential_concerns": ["Expected salary is slightly high"],
    "skills_match": 90.0,
    "experience_match": 85.0,
    "salary_match": 80.0,
    "location_match": 100.0,
    "overall_match_percentage": 85.0
  },
  "job_info": {
    "id": 2,
    "name": "Senior Software Engineer",
    "location": "San Francisco, CA",
    "salary_range": "$110,000 - $130,000"
  },
  "recommended_actions": [
    "Schedule next round interview",
    "Request reference checks from candidate",
    "Send technical assessment test",
    "Review portfolio and key projects"
  ]
}
```

Error responses:
- 400: Candidate is not in `new` status.
```json
{
  "non_field_errors": [
    "Candidate must have 'new' status to be shortlisted."
  ]
}
```
- 404: Candidate not found.
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/meeting/

Description: Schedules an interview meeting for a shortlisted candidate. Creates a Zoom meeting, sends an invitation email to the candidate's email, and sets the candidate status to `interviewing`.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "meeting_time": "2026-07-20T10:00:00Z",
  "duration": 60,
  "agenda": "Technical Interview - Django & Architecture"
}
```

Success response (201):

```json
{
  "message": "Interview meeting scheduled and invitation email sent successfully.",
  "zoom_warning": "Zoom meeting creation failed: Invalid access token, does not contain scopes:[meeting:write:meeting]. A mock Zoom link was generated instead.",
  "candidate": {
    "id": 1,
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "status": "interviewing",
    "phone": "+15550199",
    "location": "San Francisco, CA",
    "experience": 5,
    "skills": ["Python", "Django", "React"],
    "current_salary": "$120,000",
    "expected_salary": "$140,000",
    "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
    "applied": "2026-06-20T10:00:00.123456Z",
    "applied_at": "2026-06-20T10:00:00.123456Z"
  },
  "meeting": {
    "id": 5,
    "candidate": 1,
    "agency": 1,
    "user": 2,
    "meeting_time": "2026-07-20T10:00:00Z",
    "agenda": "Technical Interview - Django & Architecture",
    "summary": "Interview scheduled via Zoom: Interview with Jane Smith for Senior Software Engineer",
    "meeting_link": "https://zoom.us/j/1234567890",
    "status": "scheduled",
    "created_at": "2026-06-22T06:00:00.123456Z",
    "updated_at": "2026-06-22T06:00:00.123456Z"
  }
}
```

Error responses:
- 400: Validation error or Zoom not connected.
```json
{
  "non_field_errors": [
    "Zoom is not connected. Please connect your Zoom account first."
  ]
}
```
- 404: Candidate not found.
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/offer/

Description: Sends a job offer with salary and notice period fields to a shortlisted/interviewing candidate. Transitions candidate status to `offered` and creates a `Placement` object.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "salary": "135000.00",
  "notice_period": 30
}
```

Success response (201):

```json
{
  "message": "Offer sent and placement created successfully.",
  "candidate": {
    "id": 1,
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "status": "offered",
    "phone": "+15550199",
    "location": "San Francisco, CA",
    "experience": 5,
    "skills": ["Python", "Django", "React"],
    "current_salary": "$120,000",
    "expected_salary": "$140,000",
    "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
    "applied": "2026-06-20T10:00:00.123456Z",
    "applied_at": "2026-06-20T10:00:00.123456Z"
  },
  "placement": {
    "id": 3,
    "candidate": 1,
    "job": 2,
    "agency": 1,
    "user": 2,
    "salary": "135000.00",
    "notice_period": 30,
    "status": "placed",
    "created_at": "2026-06-22T06:00:00.123456Z",
    "updated_at": "2026-06-22T06:00:00.123456Z"
  }
}
```

Error responses:
- 400: Candidate is not in `shortlisted` or `interviewing` status.
```json
{
  "non_field_errors": [
    "Candidate must be shortlisted or interviewing to send an offer."
  ]
}
```
- 404: Candidate not found.
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/accept/

Description: Accepts a candidate from any status. Sets the status to `accepted` and updates the related placement status to `placed` if it exists.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "+15550199",
  "location": "San Francisco, CA",
  "experience": 5,
  "skills": ["Python", "Django", "React"],
  "current_salary": "$120,000",
  "expected_salary": "$140,000",
  "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
  "status": "accepted",
  "applied": "2026-06-20T10:00:00.123456Z",
  "applied_at": "2026-06-20T10:00:00.123456Z"
}
```

Error responses:
- 404: Candidate not found.
```json
{ "detail": "Candidate not found" }
```

---

## POST /api/v1/agency/candidates/<id>/reject/

Description: Rejects a candidate from any status. Sets the status to `rejected` and updates the related placement status to `not_placed` if it exists.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "+15550199",
  "location": "San Francisco, CA",
  "experience": 5,
  "skills": ["Python", "Django", "React"],
  "current_salary": "$120,000",
  "expected_salary": "$140,000",
  "resume": "http://localhost:8000/media/candidates/resumes/resume.pdf",
  "status": "rejected",
  "applied": "2026-06-20T10:00:00.123456Z",
  "applied_at": "2026-06-20T10:00:00.123456Z"
}
```

Error responses:
- 404: Candidate not found.
```json
{ "detail": "Candidate not found" }
```
