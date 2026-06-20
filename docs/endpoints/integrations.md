# Integrations Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- GET  `/api/v1/integrations/`
- GET  `/api/v1/integrations/zoom/connect/`
- GET  `/api/v1/integrations/zoom/callback/`
- POST `/api/v1/integrations/zoom/disconnect/`
- POST `/api/v1/integrations/zoom/meetings/create/`

---

## GET /api/v1/integrations/

Description: List all integrations for the authenticated user within the specified agency.

Auth: Required

Headers:

- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>`

Success response (200):

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "provider": "zoom",
    "is_connected": true,
    "connected_at": "2025-07-20T10:00:00Z",
    "metadata": {
      "zoom_user_id": "abc123",
      "email": "jane@example.com",
      "display_name": "Jane Example",
      "account_id": "xyz789"
    },
    "created_at": "2025-07-20T10:00:00Z",
    "updated_at": "2025-07-20T10:00:00Z"
  }
]
```

Error responses:

- 400: Missing agency header
```json
{ "error": "X-Agency-ID header is required" }
```

---

## GET /api/v1/integrations/zoom/connect/

Description: Generate the Zoom OAuth authorization URL. The frontend should redirect the user to this URL to begin the Zoom connection flow.

Auth: Required

Headers:

- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>`

Success response (200):

```json
{
  "auth_url": "https://zoom.us/oauth/authorize?response_type=code&client_id=XXX&redirect_uri=XXX&state=user_id:agency_id"
}
```

Error responses:

- 400: Missing agency header
```json
{ "error": "X-Agency-ID header is required" }
```

Notes: The `state` parameter encodes `user_id:agency_id` so the OAuth callback can identify who authorized the connection. The frontend should redirect the user to the returned `auth_url`.

---

## GET /api/v1/integrations/zoom/callback/

Description: OAuth callback endpoint that Zoom redirects to after user authorization. Exchanges the authorization code for tokens, stores them, and redirects to the frontend.

Auth: Not required (public — called by Zoom redirect)

Query Parameters:

| Parameter | Type | Description |
|---|---|---|
| `code` | string | Authorization code from Zoom |
| `state` | string | `user_id:agency_id` passed during authorization |

Success: Redirects to `{FRONTEND_URL}/integrations?status=success&provider=zoom`

Error: Redirects to `{FRONTEND_URL}/integrations?status=error&message=<reason>`

Possible error messages:

- `missing_code` — No authorization code in the callback
- `missing_state` — No state parameter
- `invalid_state` — State parameter format is invalid
- `invalid_user_or_agency` — User or agency not found
- `token_exchange_failed` — Failed to exchange code for tokens with Zoom

Notes: This endpoint is registered as the Redirect URL in the Zoom App Marketplace. It should not be called directly by the frontend.

---

## POST /api/v1/integrations/zoom/disconnect/

Description: Disconnect the user's Zoom integration. Revokes the Zoom OAuth token and removes stored credentials.

Auth: Required

Headers:

- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>`

Success response (200):

```json
{ "message": "Zoom integration disconnected successfully" }
```

Error responses:

- 400: Missing agency header
```json
{ "error": "X-Agency-ID header is required" }
```
- 404: No Zoom integration found
```json
{ "error": "Zoom integration not found" }
```

---

## POST /api/v1/integrations/zoom/meetings/create/

Description: Create a scheduled Zoom meeting using the user's connected Zoom account.

Auth: Required

Headers:

- `Authorization: Bearer <access_token>`
- `X-Agency-ID: <agency_id>`

Request JSON:

```json
{
  "topic": "Team Standup",
  "start_time": "2025-07-20T10:00:00Z",
  "duration": 30,
  "agenda": "Weekly sync and progress review"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `topic` | string | Yes | Meeting title (max 200 chars) |
| `start_time` | datetime | Yes | Start time in ISO 8601 format |
| `duration` | integer | Yes | Duration in minutes (1–1440) |
| `agenda` | string | No | Meeting agenda (max 2000 chars) |

Success response (201):

```json
{
  "message": "Meeting created successfully",
  "meeting": {
    "id": 12345678901,
    "topic": "Team Standup",
    "start_time": "2025-07-20T10:00:00Z",
    "duration": 30,
    "join_url": "https://zoom.us/j/12345678901?pwd=xxxx",
    "start_url": "https://zoom.us/s/12345678901?zak=xxxx",
    "password": "abc123"
  }
}
```

Error responses:

- 400: Missing agency header
```json
{ "error": "X-Agency-ID header is required" }
```
- 400: Zoom not connected
```json
{ "error": "Zoom is not connected. Please connect your Zoom account first." }
```
- 400: Tokens missing
```json
{ "error": "Zoom tokens not found. Please reconnect your Zoom account." }
```
- 400: Validation errors
```json
{ "topic": ["This field is required."] }
```
- 502: Zoom API failure
```json
{ "error": "Failed to create meeting on Zoom. Please try again." }
```

Curl example:

```bash
curl -X POST http://localhost:8000/api/v1/integrations/zoom/meetings/create/ \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Agency-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Team Standup",
    "start_time": "2025-07-20T10:00:00Z",
    "duration": 30,
    "agenda": "Weekly sync"
  }'
```

---

## Zoom OAuth Flow Overview

1. Frontend calls `GET /api/v1/integrations/zoom/connect/` → receives `auth_url`
2. Frontend redirects user to `auth_url` (Zoom consent screen)
3. User authorizes → Zoom redirects to `GET /api/v1/integrations/zoom/callback/?code=XXX&state=user_id:agency_id`
4. Backend exchanges code for tokens, fetches Zoom user profile, stores everything
5. Backend redirects to `{FRONTEND_URL}/integrations?status=success&provider=zoom`
6. Frontend shows success state — user can now create meetings

### Environment Variables

| Variable | Description |
|---|---|
| `ZOOM_CLIENT_ID` | Zoom OAuth app client ID |
| `ZOOM_CLIENT_SECRET` | Zoom OAuth app client secret |
| `ZOOM_REDIRECT_URI` | Callback URL registered in Zoom Marketplace |
| `ZOOM_SECRET_TOKEN` | Zoom webhook verification token |
| `FRONTEND_URL` | Frontend base URL for post-OAuth redirect |
| `BACKEND_URL` | Backend base URL |
