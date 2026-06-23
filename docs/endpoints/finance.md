# Finance Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- `POST /api/v1/finance/clients/<int:client_id>/revenue/`

---

## `POST /api/v1/finance/clients/<int:client_id>/revenue/`

### Description

Record client revenue for a given client under the current agency.

### Auth

- `Required` (Authenticated user must be an active member of the agency specified by the `X-Agency-ID` header)

### Request Payload Reference

```json
{
  "amount": "15000.00"
}
```

### Response Payload Reference

Success example (Status: `201 Created`):

```json
{
  "id": 1,
  "client": 3,
  "agency": 2,
  "amount": "15000.00",
  "added_by": 5,
  "created_at": "2026-06-23T11:15:00Z",
  "updated_at": "2026-06-23T11:15:00Z"
}
```

Error example (Status: `400 Bad Request`):

```json
{
  "amount": [
    "Revenue amount must be greater than zero."
  ]
}
```
