# Main Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- `POST /api/v1/main/contact/` — Post/create a contact message (public)
- `GET /api/v1/main/search/` — Search dashboard data for active agency (authenticated)

---

## `POST /api/v1/main/contact/`

### Description

Post/create a contact message from the public contact form.

### Auth

- `Not required`

### Request Payload Reference

```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "company_name": "Example Corp",
  "subject": "Inquiry",
  "message": "Hello, I would like to know more about your services."
}
```

### Response Payload Reference

```json
{
  "id": 1,
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "company_name": "Example Corp",
  "subject": "Inquiry",
  "message": "Hello, I would like to know more about your services.",
  "created_at": "2026-07-06T11:00:00Z"
}
```

---

## `GET /api/v1/main/search/`

### Description

Search leads, candidates, clients, and jobs matching the query parameter, scoped to the current user's active agency.

### Auth

- `Required`
- Header: `X-Agency-ID` (ID of the active agency)

### Query Parameters

- `query` (string, required): The search keyword to filter by.

### Response Payload Reference

```json
[
  {
    "object_id": 12,
    "title": "Acme Corporation",
    "description": "Technology",
    "result_source": "leads"
  },
  {
    "object_id": 4,
    "title": "John Smith",
    "description": "Senior Python Developer",
    "result_source": "candidates"
  }
]
```

### Error Responses

- **400 Bad Request** (Missing query parameter):
  ```json
  {
    "error": "Query parameter is required."
  }
  ```
- **400 Bad Request** (Missing `X-Agency-ID` header):
  ```json
  {
    "error": "X-Agency-ID header is required."
  }
  ```

### Related Tests

- None

