# Agency Dashboard Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/dashboard/` — Retrieve comprehensive dashboard statistics, trends, and health lists for the agency.

---

## `GET /api/v1/agency/dashboard/`

### Description

Retrieves the dashboard data metrics, revenue YTD summary, recruitment workload/pipeline loads, upcoming interviews, hot candidates, and recruitment funnel stages (applications, shortlisted, interviews, placed) for the active agency.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header

### Query Parameters

None.

### Response Payload Reference

Success example:

```json
{
  "active_jobs": {
    "value": 4,
    "trend": "+12%"
  },
  "total_candidates": {
    "value": 4,
    "trend": "+28%"
  },
  "active_clients": {
    "value": 3,
    "trend": "+5%"
  },
  "placements_mtd": {
    "value": 8,
    "trend": "+15%"
  },
  "revenue_overview": {
    "total_revenue_ytd": 365000.0,
    "currency_symbol": "£",
    "trend_ytd": "+34%",
    "monthly_data": [
      { "month": "Jan", "revenue": 10000.0 },
      { "month": "Feb", "revenue": 50000.0 },
      { "month": "Mar", "revenue": 45000.0 },
      { "month": "Apr", "revenue": 80000.0 },
      { "month": "May", "revenue": 70000.0 },
      { "month": "Jun", "revenue": 110000.0 }
    ]
  },
  "active_positions": {
    "open_jobs_count": 12,
    "trend": "+15%",
    "monthly_data": [
      { "month": "Jan", "pipeline_load": 4000 },
      { "month": "Feb", "pipeline_load": 3000 },
      { "month": "Mar", "pipeline_load": 2000 },
      { "month": "Apr", "pipeline_load": 2800 },
      { "month": "May", "pipeline_load": 1900 },
      { "month": "Jun", "pipeline_load": 2400 }
    ]
  },
  "upcoming_interviews": [
    {
      "id": 1,
      "candidate_name": "Sarah Martinez",
      "job_title": "Senior Software Engineer",
      "meeting_time": "2026-06-10T14:00:00Z",
      "formatted_meeting_time": "10/06/2026 at 14:00"
    }
  ],
  "hot_candidates": [
    {
      "id": 1,
      "name": "Alex Thompson",
      "job_title": "Senior Software Engineer",
      "match_percentage": 92
    }
  ],
  "pipeline_health": {
    "applications": 4,
    "shortlisted": 2,
    "interview_stage": 1,
    "placed": 8
  }
}
```

### Related Tests

- None
