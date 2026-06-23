# Agency Interviews Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/interviews/` — List agency interviews with pagination, status filters, search, and summary counts
- `GET /api/v1/agency/interviews/calendar/` — List agency interviews for a specific month and year with minimal fields

---

## `GET /api/v1/agency/interviews/`

### Description

Retrieves a paginated list of candidate meetings (interviews) for the active agency. Suppports filtering by meeting status and keyword searching across candidate name, job title, and client company name. Returns summary statistics for scheduled, completed, and weekly meetings.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `page` | integer | No | Page number for paginated results (default: `1`) |
| `page_size` | integer | No | Number of records per page (default: `10`, max: `100`) |
| `status` | string | No | Filter by meeting status: `upcoming` (scheduled or pending), `completed`, `scheduled`, `pending`, `cancelled`, or `all` |
| `search` | string | No | Search query matching candidate name, job title, or client company name |

### Response Payload Reference

Success example:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "candidate": 1,
      "candidate_name": "Sarah Martinez",
      "candidate_status": "interviewing",
      "job_title": "Senior Software Engineer",
      "job_id": 1,
      "client_name": "GlobalTech Industries",
      "meeting_time": "2026-06-10T14:00:00Z",
      "meeting_link": "https://zoom.us/j/6362583775",
      "status": "scheduled"
    },
    {
      "id": 4,
      "candidate": 2,
      "candidate_name": "James Wilson",
      "candidate_status": "interviewing",
      "job_title": "Product Manager",
      "job_id": 2,
      "client_name": "GlobalTech Industries",
      "meeting_time": "2026-06-08T10:00:00Z",
      "meeting_link": "https://zoom.us/j/7362583776",
      "status": "scheduled"
    }
  ],
  "scheduled_count": 2,
  "completed_count": 0,
  "this_week_count": 2
}
```

### Related Tests

- None

---

## `GET /api/v1/agency/interviews/calendar/`

### Description

Retrieves a list of candidate meetings (interviews) for a specific month and year, returning only lightweight fields (id, meeting time, candidate name, and position). Useful for loading events in calendar views.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `year` | integer | No | The calendar year to filter by (default: current year) |
| `month` | integer | No | The calendar month (1-12) to filter by (default: current month) |

### Response Payload Reference

Success example:

```json
[
  {
    "id": 2,
    "meeting_time": "2026-06-16T12:33:00Z",
    "candidate_name": "Sarah Martinez",
    "position": "Senior Software Engineer"
  },
  {
    "id": 3,
    "meeting_time": "2026-06-23T12:37:00Z",
    "candidate_name": "James Wilson",
    "position": "Product Manager"
  }
]
```

