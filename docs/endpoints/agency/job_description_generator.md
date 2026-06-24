# Generate Job Description

## `POST /api/v1/agency/jobs/generate-description/`

Generate a structured job description from a document and/or freeform text using AI.

**Authentication:** Required (JWT)
**Header:** `X-Agency-ID` (required)

### Request

**Content-Type:** `multipart/form-data`

| Field      | Type   | Required | Description                                      |
|------------|--------|----------|--------------------------------------------------|
| `document` | File   | No*      | PDF, DOCX, or TXT file containing job information |
| `text`     | String | No*      | Freeform text describing the job role              |

> **\*** At least one of `document` or `text` must be provided. Both can be sent together.

### Success Response — `200 OK`

Returned when the AI successfully generates a job description.

```json
{
  "success": true,
  "error_message": null,
  "job_title": "Senior Software Engineer",
  "company_name": "TechCorp",
  "department": "Engineering",
  "industry": "Technology",
  "employment_type": "Full-time",
  "work_mode": "Remote",
  "location": "San Francisco, CA",
  "minimum_experience": 5.0,
  "maximum_experience": 8.0,
  "minimum_salary": "150000",
  "maximum_salary": "200000",
  "currency": "USD",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "preferred_skills": ["Kubernetes", "AWS"],
  "required_languages": ["English"],
  "required_certifications": [],
  "required_degree": "Bachelor's in Computer Science",
  "preferred_degree": "Master's in Computer Science",
  "summary": "We are looking for a Senior Software Engineer to join our Engineering team...",
  "responsibilities": [
    "Design and implement scalable backend services",
    "Mentor junior developers"
  ],
  "requirements": [
    "5+ years of experience with Python",
    "Strong knowledge of relational databases"
  ],
  "benefits": [
    "Competitive salary",
    "Remote work flexibility",
    "Health insurance"
  ],
  "full_description": "## Senior Software Engineer\n\nTechCorp is seeking a Senior Software Engineer..."
}
```

### Error Response — `422 Unprocessable Entity`

Returned when the AI determines the input is unrelated or cannot produce a job description.

```json
{
  "error": "The provided text appears to be a cooking recipe and does not contain job-related information."
}
```

### Error Response — `400 Bad Request`

Returned when validation fails (no input, unsupported file type).

```json
{
  "detail": "At least one of 'document' or 'text' must be provided."
}
```

**Unsupported file type:**

```json
{
  "detail": "Unsupported file type: .jpg. Supported types: .pdf, .docx, .txt"
}
```
