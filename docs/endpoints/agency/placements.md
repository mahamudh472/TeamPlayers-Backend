# Agency Placements Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/placements/` — List agency placements with pagination, status filters, search, and summary counts

---

## `GET /api/v1/agency/placements/`

### Description

Retrieves a paginated list of successful placements for the active agency. Supports status filtering via the `status` query parameter (tabs: `all`, `offers`, `active`) and keyword searching across candidate name, candidate email, job title, and client company name. Returns summary statistics for offers, active (placed), and total placements.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `page` | integer | No | Page number for paginated results (default: `1`) |
| `page_size` | integer | No | Number of records per page (default: `10`, max: `100`) |
| `status` | string | No | Filter by tab: `all` (offered + placed), `offers` (candidate status is `'offered'`), or `active` (candidate status is `'accepted'`) |
| `search` | string | No | Search query matching candidate name, candidate email, job title, or client company |

### Response Payload Reference

Success example:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "candidate_id": 1,
      "candidate_name": "Md Mahmud Hasan",
      "candidate_email": "mahmud@example.com",
      "position": "Senior Software Engineer",
      "client": "GlobalTech Industries",
      "salary": "130000.00",
      "placed_date": "22/06/2026",
      "status": "placed"
    }
  ],
  "all_count": 1,
  "offers_count": 0,
  "active_count": 1
}
```

### Related Tests

- None
