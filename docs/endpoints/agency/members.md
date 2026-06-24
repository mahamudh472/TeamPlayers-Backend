# Agency Team Member Endpoints

Back to index: [ENDPOINT_LIST.md](../../ENDPOINT_LIST.md)

- `GET /api/v1/agency/members/` — Retrieve the list of active team members.
- `POST /api/v1/agency/members/` — Invite a user to join the agency.
- `PATCH /api/v1/agency/members/<id>/` — Update an agency member's role.
- `DELETE /api/v1/agency/members/<id>/` — Remove a member from the agency.
- `GET /api/v1/agency/members/accept-invite/` — Public link to accept an invitation.

---

## `GET /api/v1/agency/members/`

### Description

Retrieves the list of active team members (both accepted and pending) for the active agency.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.

### Response Payload Reference

Success example (200 OK):

```json
[
  {
    "id": 1,
    "user_id": "848dbb08-3a9d-4767-bead-5527f525bf78",
    "email": "owner@teamplayers.com",
    "full_name": "Jane Doe",
    "role": "owner",
    "invitation_status": "accepted",
    "is_active": true,
    "created_at": "2026-06-24T06:12:00Z",
    "updated_at": "2026-06-24T06:12:00Z"
  },
  {
    "id": 2,
    "user_id": "fcd3a824-34c9-4672-8874-124b896da991",
    "email": "recruiter@teamplayers.com",
    "full_name": "John Smith",
    "role": "recruiter",
    "invitation_status": "pending",
    "is_active": true,
    "created_at": "2026-06-24T06:15:00Z",
    "updated_at": "2026-06-24T06:15:00Z"
  }
]
```

---

## `POST /api/v1/agency/members/`

### Description

Invites a user to the agency by email with a specified role.
- If the user exists: Creates a pending membership and emails them a secure invitation link.
- If the user does not exist: Creates the user with a random password, adds them directly to the agency, and emails them their login credentials.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.
- Must be Owner or Admin.

### Request Payload

| Field | Type | Description | Required | Choices |
| :--- | :--- | :--- | :--- | :--- |
| `email` | string | The email address of the user to invite | Yes | |
| `role` | string | The role to assign to the user | Yes | `admin`, `recruiter` |

Request example:

```json
{
  "email": "new.member@teamplayers.com",
  "role": "recruiter"
}
```

### Response Payload Reference

Success example (201 Created):

```json
{
  "id": 3,
  "user_id": "a291f09d-cbbe-4f10-ae4b-91cc2fbe9871",
  "email": "new.member@teamplayers.com",
  "full_name": null,
  "role": "recruiter",
  "invitation_status": "pending",
  "is_active": true,
  "created_at": "2026-06-24T06:17:00Z",
  "updated_at": "2026-06-24T06:17:00Z"
}
```

---

## `PATCH /api/v1/agency/members/<id>/`

### Description

Updates the role of a specific agency member.
- Owners can update anyone's role (including transferring ownership or appointing other admins).
- Admins can update roles of recruiters or other admins, but cannot modify the owner's role or promote anyone to owner.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.
- Must be Owner or Admin.

### Request Payload

| Field | Type | Description | Required | Choices |
| :--- | :--- | :--- | :--- | :--- |
| `role` | string | The new role to assign to the member | Yes | `owner`, `admin`, `recruiter` |

Request example:

```json
{
  "role": "admin"
}
```

### Response Payload Reference

Success example (200 OK):

```json
{
  "id": 3,
  "user_id": "a291f09d-cbbe-4f10-ae4b-91cc2fbe9871",
  "email": "new.member@teamplayers.com",
  "full_name": null,
  "role": "admin",
  "invitation_status": "pending",
  "is_active": true,
  "created_at": "2026-06-24T06:17:00Z",
  "updated_at": "2026-06-24T06:18:00Z"
}
```

---

## `DELETE /api/v1/agency/members/<id>/`

### Description

Removes a member from the agency.
- Owners can remove any member (except themselves from this endpoint).
- Admins can remove recruiters and other admins, but cannot remove the owner.

### Auth

- Required (JWT Bearer Token)
- Requires `X-Agency-ID` header specifying the active agency ID.
- Must be Owner or Admin.

### Response Payload Reference

Success example (200 OK):

```json
{
  "message": "Member removed successfully"
}
```

---

## `GET /api/v1/agency/members/accept-invite/`

### Description

Public GET endpoint used to accept an agency invitation. When a user clicks this link in their email:
1. The backend validates the cryptographic signature of the token.
2. Marks the invitation status as `accepted`.
3. Redirects the user to the frontend login page (`FRONTEND_URL/login?invite_accepted=true`).

### Auth

- Public (AllowAny)

### Query Parameters

| Parameter | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `token` | string | Cryptographically signed invitation token | Yes |
