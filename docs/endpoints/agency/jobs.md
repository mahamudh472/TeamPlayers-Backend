# Agency Jobs Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

## Endpoint Inventory

- GET `/api/v1/agency/jobs/` — List jobs with search, pagination, and static summary metrics.
- POST `/api/v1/agency/jobs/` — Create a new job.
- GET `/api/v1/agency/jobs/<id>/` — Retrieve details of a single job.
- PATCH `/api/v1/agency/jobs/<id>/` — Update details of a single job.
- GET `/api/v1/agency/jobs/<id>/candidates/` — List candidates for a specific job.
- GET `/api/v1/agency/jobs/public/` — Public list of active (open) jobs with pagination and search.
- GET `/api/v1/agency/jobs/public/<id>/` — Public details of a single active (open) job.

---

## GET /api/v1/agency/jobs/

Description: Retrieve all jobs belonging to the agency. Results can be paginated and filtered using the `search` query parameter. The search matches against title, description, location, or client company. Includes dynamic summary metrics: `active_jobs`, `total_applicants`, `shortlisted`, and `interviewed`. Each list item also includes dynamic `applicants`, `shortlisted`, and `interviewed` metrics.

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
  "interviewed": 5,
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
      "skills_weight": 30.0,
      "experience_weight": 25.0,
      "salary_weight": 15.0,
      "location_weight": 15.0,
      "certification_weight": 15.0,
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

Description: Create a new job associated with the agency and client. If scoring priority weights (`skills_weight`, `experience_weight`, `salary_weight`, `location_weight`, `certification_weight`) are omitted, AI analyzes the job description to calculate them automatically.

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
  "skills_weight": 30.0,
  "experience_weight": 25.0,
  "salary_weight": 15.0,
  "location_weight": 15.0,
  "certification_weight": 15.0,
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
  "skills_weight": 30.0,
  "experience_weight": 25.0,
  "salary_weight": 15.0,
  "location_weight": 15.0,
  "certification_weight": 15.0,
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

Description: Partially update details of a single job, including manual adjustments to scoring weights (`skills_weight`, `experience_weight`, `salary_weight`, `location_weight`, `certification_weight`). Updating weights automatically recalculates the overall match scores of candidates applied to this job.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Request JSON:

```json
{
  "status": "closed",
  "skills_weight": 35.0,
  "certification_weight": 10.0
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
  "skills_weight": 35.0,
  "experience_weight": 25.0,
  "salary_weight": 15.0,
  "location_weight": 15.0,
  "certification_weight": 10.0,
  "applicants": 12,
  "shortlisted": 4,
  "interviewed": 2,
  "created_at": "2026-06-18T12:00:00.123456Z",
  "updated_at": "2026-06-18T12:07:00.123456Z"
}
```

Error responses:
- 400: Weight sum validation error
```json
{
  "non_field_errors": [
    "The sum of priority weights must equal 100. Current sum is 95.0."
  ]
}
```
- 404: Job not found
```json
{ "detail": "Job not found" }
```

---

## GET /api/v1/agency/jobs/<id>/candidates/

Description: Retrieve all candidates applying for the specified job.

Auth: Required (Bearer access token)

Headers:
- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>` (Required)

Success response (200):

```json
[
  {
    "id": 1,
    "name": "Jane Smith",
    "ai_average_score": 85.0,
    "status": "new",
    "location": "San Francisco, CA",
    "experience": 5
  }
]
```

Error responses:
- 404: Job not found
```json
{ "detail": "Job not found" }
```

---

## GET /api/v1/agency/jobs/public/

Description: Retrieve all active (open) jobs across all agencies for public display. Results are paginated and can be filtered using the `search` query parameter matching against title, description, or location. Client identities are hidden for confidentiality.

Auth: None (Public)

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
  "results": [
    {
      "id": 1,
      "agency_name": "Tech Recruitment Ltd",
      "agency_logo": "http://localhost:8000/media/agencies/logos/tech_rec.png",
      "title": "Senior Python Developer",
      "location": "Boston, MA",
      "salary_range": "$110k - $130k",
      "experince_required": 5,
      "skills": ["Python", "Django", "PostgreSQL"],
      "job_type": "remote",
      "created_at": "2026-06-18T12:00:00.123456Z"
    }
  ]
}
```

---

## GET /api/v1/agency/jobs/public/<id>/

Description: Retrieve public details of a single active (open) job by its ID. Client identities are hidden.

Auth: None (Public)

Success response (200):

```json
{
  "id": 1,
  "agency_name": "Tech Recruitment Ltd",
  "agency_logo": "http://localhost:8000/media/agencies/logos/tech_rec.png",
  "title": "Senior Python Developer",
  "location": "Boston, MA",
  "salary_range": "$110k - $130k",
  "experince_required": 5,
  "skills": ["Python", "Django", "PostgreSQL"],
  "job_type": "remote",
  "created_at": "2026-06-18T12:00:00.123456Z",
  "description": "Develop and maintain robust web services and integrations.",
  "description_file": null
}
```

Error responses:
- 404: Job not found
```json
{ "detail": "Job not found" }
```

