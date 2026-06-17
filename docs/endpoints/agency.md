# Agency Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- GET `/api/v1/agency/leads/` — List agency leads, filterable by status, with status counts.
- GET `/api/v1/agency/leads/<id>/` — Retrieve details of a single lead, including its notes.
- POST `/api/v1/agency/leads/<id>/notes/` — Add a new note for a lead.
- PATCH `/api/v1/agency/leads/<id>/status/` — Change a lead's status.
- POST `/api/v1/agency/webhooks/leads/` — Bulk lead ingestion webhook (unauthenticated, secret-verified).

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


