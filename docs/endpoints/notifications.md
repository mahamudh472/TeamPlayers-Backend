# Notifications Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- `GET /api/v1/notifications/`
- `POST /api/v1/notifications/<notification_id>/read/`
- `POST /api/v1/notifications/read-all/`
- `POST /api/v1/notifications/send-test/`
- `WebSocket /ws/notifications/`

---

## `GET /api/v1/notifications/`

### Description

Retrieves a paginated list of notifications for the authenticated user, ordered by creation date descending.

### Auth

- `Required`

### Query Parameters

- `page` (optional): Page number (default: 1)
- `page_size` (optional): Number of items per page (default: 15, max: 100)

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
      "title": "New Lead: Acme Corp",
      "message": "A new lead Acme Corp has been added by integration.",
      "is_read": false,
      "notification_type": "new_lead",
      "source": {
        "id": 42,
        "type": "lead"
      },
      "created_at": "2026-07-07T06:54:07.009940Z",
      "updated_at": "2026-07-07T06:54:07.009949Z"
    }
  ]
}
```

---

## `POST /api/v1/notifications/<notification_id>/read/`

### Description

Marks a specific notification as read.

### Auth

- `Required`

### Response Payload Reference

Success example:

```json
{
  "id": 1,
  "title": "New Lead: Acme Corp",
  "message": "A new lead Acme Corp has been added by integration.",
  "is_read": true,
  "notification_type": "new_lead",
  "source": {
    "id": 42,
    "type": "lead"
  },
  "created_at": "2026-07-07T06:54:07.009940Z",
  "updated_at": "2026-07-07T06:54:07.009949Z"
}
```

---

## `POST /api/v1/notifications/read-all/`

### Description

Marks all unread notifications for the user as read.

### Auth

- `Required`

### Response Payload Reference

Success example:

```json
{
  "message": "Successfully marked 1 notifications as read",
  "count": 1
}
```

---

## `POST /api/v1/notifications/send-test/`

### Description

Sends an instant test notification to the authenticated user via database creation and WebSocket real-time push.

### Auth

- `Required`

### Response Payload Reference

Success example:

```json
{
  "id": 3,
  "title": "Instant Test Notification",
  "message": "This is a test notification generated in real-time.",
  "is_read": false,
  "notification_type": "test_notification",
  "source": {
    "id": "test_id",
    "type": "test"
  },
  "created_at": "2026-07-07T06:58:00.000000Z",
  "updated_at": "2026-07-07T06:58:00.000000Z"
}
```

---

## `WebSocket /ws/notifications/`

### Description

Establishes a persistent connection for real-time notifications. When a new notification is generated for the authenticated user, it will be pushed immediately down this WebSocket.

### Connection Protocol

- `ws://` (or `wss://` for secure production connections)

### Authentication

Pass the JWT access token in the `token` query parameter:

`ws://localhost:8000/ws/notifications/?token=<ACCESS_TOKEN>`

### Message Format (Pushed by Server)

```json
{
  "type": "notification",
  "data": {
    "id": 2,
    "title": "Interview Reminder",
    "message": "You have an interview with John Doe in 1 hour.",
    "is_read": false,
    "notification_type": "interview_reminder",
    "source": {
      "id": 101,
      "type": "interview"
    },
    "created_at": "2026-07-07T06:56:00.000000Z",
    "updated_at": "2026-07-07T06:56:00.000000Z"
  }
}
```
