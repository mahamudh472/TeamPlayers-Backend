# Retrieve AI Recommendations and Hot Candidates

Retrieve lists of AI Recommendations and Hot Candidates tailored for the active agency, filtered and scored based on AI analysis.

- **URL:** `/api/v1/agency/recommendations/`
- **Method:** `GET`
- **Headers:**
  - `Authorization: Bearer <token>`
  - `X-Agency-ID: <agency_id>` (Required)

## Response

### Success Response (`200 OK`)

```json
{
  "recommendations": [
    {
      "id": "rec-candidate-followup-4",
      "type": "alert",
      "title": "High-match candidate needs follow-up",
      "description": "Md. Mahmud Hasan (92% match) has been shortlisted for 3 days",
      "actionText": "Schedule Interview",
      "actionLink": "/dashboard/candidates/4?schedule=true"
    },
    {
      "id": "rec-lead-2",
      "type": "trend",
      "title": "New high-value lead detected",
      "description": "TechCorp Ltd matches your success profile - similar to your top clients",
      "actionText": "View Lead",
      "actionLink": "/dashboard/leads"
    }
  ],
  "hot_candidates": [
    {
      "id": 4,
      "name": "Md. Mahmud Hasan",
      "role": "Senior Software Engineer",
      "matchScore": 92,
      "link": "/dashboard/candidates/4"
    }
  ]
}
```

### Error Responses

#### `400 Bad Request`
Triggered if the `X-Agency-ID` header is missing.
```json
{
  "detail": "X-Agency-ID header is required"
}
```

#### `401 Unauthorized`
Triggered if authentication is invalid or missing.
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### `403 Forbidden`
Triggered if the user is not an active member of the requested agency.
```json
{
  "detail": "You do not have permission to access this agency"
}
```
