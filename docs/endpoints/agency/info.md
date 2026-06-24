# Agency Info Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/info/` — Retrieve the active agency's name and logo.
- `PATCH /api/v1/agency/info/` — Update the active agency's name and/or logo.

---

## `GET /api/v1/agency/info/`

### Description

Retrieves the basic details (id, name, logo URL, current subscription plan, and active team size) of the active agency.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.

### Query Parameters

None.

### Response Payload Reference

Success example (200 OK):

```json
{
  "id": 1,
  "name": "Global Recruitment Group",
  "logo": "http://localhost:8000/media/agencies/logos/logo_abc.png",
  "current_plan": "Pro Plan",
  "team_size": 4
}
```

---

## `PATCH /api/v1/agency/info/`

### Description

Partially updates the active agency's name and/or logo image.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.

### Request Payload

Supported content types: `multipart/form-data`, `application/json`

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `name` | string | The name of the agency | No |
| `logo` | file | The logo image file of the agency | No |
| `current_plan` | string | **[Read-Only]** The current plan name | No |
| `team_size` | integer | **[Read-Only]** The count of active, accepted team members | No |

### Response Payload Reference

Success example (200 OK):

```json
{
  "id": 1,
  "name": "Updated Agency Name",
  "logo": "http://localhost:8000/media/agencies/logos/new_logo.png",
  "current_plan": "Pro Plan",
  "team_size": 4
}
```
