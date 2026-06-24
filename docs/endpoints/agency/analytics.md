# Agency Analytics Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/analytics/` — Retrieve comprehensive performance metrics, trends, and breakdowns for Overview, Clients, Candidates, Recruiters, and AI performance tabs.

---

## `GET /api/v1/agency/analytics/`

### Description

Retrieves structured analytics data tailored for multiple dashboard tabs. The default date range is `last_year` (last 12 months), but can be dynamically filtered using the `range` query parameter.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header

### Query Parameters

- `range` (string, optional): The timeframe to filter analytics data. Supported values:
  - `last_month` (last 30 days)
  - `last_3_months` (last 90 days)
  - `last_year` (last 365 days) — **Default**
  - `all_time` (no date filtering)

### Response Payload Reference

Success example:

```json
{
  "overview": {
    "placement_rate": 84.6,
    "avg_days_to_fill": 22,
    "active_pipelines": 18,
    "interviews_booked": 42,
    "revenue_placements_trend": [
      { "month": "Jan", "revenue": 35000.0, "placements": 2 },
      { "month": "Feb", "revenue": 40000.0, "placements": 3 },
      { "month": "Mar", "revenue": 50000.0, "placements": 4 },
      { "month": "Apr", "revenue": 45000.0, "placements": 3 },
      { "month": "May", "revenue": 65000.0, "placements": 5 },
      { "month": "Jun", "revenue": 75000.0, "placements": 6 }
    ],
    "pipeline_distribution": {
      "new": 10,
      "shortlisted": 20,
      "interviewing": 5,
      "offered": 2,
      "accepted": 10,
      "rejected": 8
    },
    "placements_by_industry": [
      { "industry": "Technology", "count": 8 },
      { "industry": "Finance", "count": 5 },
      { "industry": "Healthcare", "count": 3 },
      { "industry": "Retail", "count": 4 },
      { "industry": "Manufacturing", "count": 6 }
    ],
    "currency_symbol": "£"
  },
  "clients": {
    "total_clients": 5,
    "avg_jobs_per_client": 0.4,
    "avg_client_success_rate": 10.0,
    "top_clients": [
      {
        "id": 1,
        "company": "Partner Company A",
        "industry": "Finance",
        "active_jobs": 0,
        "placements_count": 0,
        "revenue": 10000.0,
        "success_rate": 0.0
      }
    ]
  },
  "candidates": {
    "total_applications": 5,
    "top_skill_match": "Python (3 profiles)",
    "primary_experience_bracket": "Mid (3-5 yrs)",
    "experience_distribution": [
      { "level": "Entry (0-2 yrs)", "count": 2 },
      { "level": "Mid (3-5 yrs)", "count": 3 },
      { "level": "Senior (6+ yrs)", "count": 0 }
    ],
    "top_skills": [
      { "skill": "Python", "count": 3 },
      { "skill": "Django", "count": 3 },
      { "skill": "Javascript", "count": 2 }
    ]
  },
  "recruiters": [
    {
      "id": 2,
      "name": "Jane Doe",
      "role": "recruiter",
      "placements_count": 8,
      "interviews_count": 22
    }
  ],
  "ai_performance": {
    "avg_overall_match_score": 78.5,
    "avg_placed_match_score": 88.0,
    "avg_rejected_match_score": 45.2
  }
}
```

### Related Tests

- None
