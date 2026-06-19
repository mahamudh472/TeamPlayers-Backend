# API Endpoints Index

This index lists available API endpoints and links to the per-app reference pages under `docs/endpoints/`.

### Accounts

- [POST /api/v1/accounts/register/](endpoints/accounts.md) — Register a new user (sends OTP email)
- [POST /api/v1/accounts/verify-email/](endpoints/accounts.md) — Verify email with OTP
- [POST /api/v1/accounts/login/](endpoints/accounts.md) — Obtain JWT access and refresh tokens
- [POST /api/v1/accounts/token/refresh/](endpoints/accounts.md) — Refresh JWT access token
- [POST /api/v1/accounts/logout/](endpoints/accounts.md) — Logout / revoke session (authenticated)
- [POST /api/v1/accounts/password-reset/](endpoints/accounts.md) — Send OTP to reset password
- [POST /api/v1/accounts/check-otp/](endpoints/accounts.md) — Validate an OTP
- [POST /api/v1/accounts/password-reset-confirm/](endpoints/accounts.md) — Confirm password reset with OTP
- [POST /api/v1/accounts/change-password/](endpoints/accounts.md) — Change password (authenticated)
- [GET  /api/v1/accounts/profile/](endpoints/accounts.md) — Get current user's profile (authenticated)
- [PATCH /api/v1/accounts/profile/update/](endpoints/accounts.md) — Partial update profile (authenticated)

---

### Agency

- [GET  /api/v1/agency/leads/](endpoints/agency.md) — List agency leads, filterable by status, with status counts (authenticated)
- [GET  /api/v1/agency/leads/<id>/](endpoints/agency.md) — Retrieve details of a single lead, including its notes (authenticated)
- [POST /api/v1/agency/leads/<id>/notes/](endpoints/agency.md) — Add a new note for a lead (authenticated)
- [PATCH /api/v1/agency/leads/<id>/status/](endpoints/agency.md) — Change a lead's status (authenticated)
- [POST /api/v1/agency/webhooks/leads/](endpoints/agency.md) — Ingest leads from external webhook (secret-verified)
- [GET  /api/v1/agency/clients/](endpoints/agency.md) — List agency clients with search, pagination, and static summary metrics (authenticated)
- [POST /api/v1/agency/clients/](endpoints/agency.md) — Create a new client manually (authenticated)
- [GET  /api/v1/agency/clients/<id>/](endpoints/agency.md) — Retrieve details of a single client (authenticated)
- [PATCH /api/v1/agency/clients/<id>/](endpoints/agency.md) — Update details of a single client (authenticated)
- [GET  /api/v1/agency/jobs/](endpoints/agency.md) — List agency jobs with search, pagination, and static summary metrics (authenticated)
- [POST /api/v1/agency/jobs/](endpoints/agency.md) — Create a new job (authenticated)
- [GET  /api/v1/agency/jobs/<id>/](endpoints/agency.md) — Retrieve details of a single job (authenticated)
- [PATCH /api/v1/agency/jobs/<id>/](endpoints/agency.md) — Update details of a single job (authenticated)

---

Add other apps here as their endpoint pages are created under `docs/endpoints/`.

