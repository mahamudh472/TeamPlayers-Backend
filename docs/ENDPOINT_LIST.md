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

- [GET  /api/v1/agency/dashboard/](endpoints/agency/dashboard.md) — Retrieve comprehensive dashboard statistics, trends, and health lists for the agency (authenticated)
- [GET  /api/v1/agency/analytics/](endpoints/agency/analytics.md) — Retrieve comprehensive performance insights, metric cards, charts, and tab details for the agency (authenticated)
- [GET  /api/v1/agency/info/](endpoints/agency/info.md) — Retrieve the active agency's name and logo (authenticated)
- [PATCH /api/v1/agency/info/](endpoints/agency/info.md) — Update the active agency's name and/or logo (authenticated)
- [GET  /api/v1/agency/members/](endpoints/agency/members.md) — Retrieve the list of active team members (authenticated)
- [POST /api/v1/agency/members/](endpoints/agency/members.md) — Invite a user to the agency by email (authenticated)
- [PATCH /api/v1/agency/members/<id>/](endpoints/agency/members.md) — Update an agency member's role (authenticated)
- [DELETE /api/v1/agency/members/<id>/](endpoints/agency/members.md) — Remove a member from the agency (authenticated)
- [GET  /api/v1/agency/members/accept-invite/](endpoints/agency/members.md) — Accept an agency invitation (public)
- [GET  /api/v1/agency/leads/](endpoints/agency/leads.md) — List agency leads, filterable by status, with status counts (authenticated)
- [GET  /api/v1/agency/leads/<id>/](endpoints/agency/leads.md) — Retrieve details of a single lead, including its notes (authenticated)
- [POST /api/v1/agency/leads/<id>/notes/](endpoints/agency/leads.md) — Add a new note for a lead (authenticated)
- [PATCH /api/v1/agency/leads/<id>/status/](endpoints/agency/leads.md) — Change a lead's status (authenticated)
- [POST /api/v1/agency/webhooks/leads/](endpoints/agency/leads.md) — Ingest leads from external webhook (secret-verified)
- [GET  /api/v1/agency/clients/](endpoints/agency/clients.md) — List agency clients with search, pagination, and static summary metrics (authenticated)
- [POST /api/v1/agency/clients/](endpoints/agency/clients.md) — Create a new client manually (authenticated)
- [GET  /api/v1/agency/clients/<id>/](endpoints/agency/clients.md) — Retrieve details of a single client (authenticated)
- [PATCH /api/v1/agency/clients/<id>/](endpoints/agency/clients.md) — Update details of a single client (authenticated)
- [GET  /api/v1/agency/clients/<id>/jobs/](endpoints/agency/clients.md) — List active jobs for a single client (authenticated)
- [GET  /api/v1/agency/clients/<id>/activities/](endpoints/agency/clients.md) — List activities for a single client (authenticated)
- [GET  /api/v1/agency/clients/<id>/notes/](endpoints/agency/clients.md) — List notes for a single client (authenticated)
- [POST /api/v1/agency/clients/<id>/notes/](endpoints/agency/clients.md) — Create a new note for a single client (authenticated)
- [GET  /api/v1/agency/jobs/](endpoints/agency/jobs.md) — List agency jobs with search, pagination, and static summary metrics (authenticated)
- [POST /api/v1/agency/jobs/](endpoints/agency/jobs.md) — Create a new job (authenticated)
- [POST /api/v1/agency/jobs/generate-description/](endpoints/agency/job_description_generator.md) — Generate a structured job description from a document and/or text using AI (authenticated)
- [GET  /api/v1/agency/jobs/<id>/](endpoints/agency/jobs.md) — Retrieve details of a single job (authenticated)
- [PATCH /api/v1/agency/jobs/<id>/](endpoints/agency/jobs.md) — Update details of a single job (authenticated)
- [GET  /api/v1/agency/jobs/<id>/candidates/](endpoints/agency/jobs.md) — List candidates for a specific job (authenticated)
- [GET  /api/v1/agency/jobs/public/](endpoints/agency/jobs.md) — Public list of active (open) jobs with pagination and search (public)
- [GET  /api/v1/agency/jobs/public/<id>/](endpoints/agency/jobs.md) — Public details of a single active (open) job (public)

- [GET  /api/v1/agency/candidates/](endpoints/agency/candidates.md) — List candidates with search, pagination, and status counts (authenticated)
- [GET  /api/v1/agency/candidates/<id>/](endpoints/agency/candidates.md) — Retrieve details of a single candidate (authenticated)
- [GET  /api/v1/agency/candidates/<id>/notes/](endpoints/agency/candidates.md) — Retrieve notes for a single candidate (authenticated)
- [POST /api/v1/agency/candidates/<id>/notes/](endpoints/agency/candidates.md) — Create a note for a single candidate (authenticated)
- [GET  /api/v1/agency/candidates/<id>/activities/](endpoints/agency/candidates.md) — Retrieve activity history for a specific candidate (authenticated)
- [POST /api/v1/agency/candidates/<id>/shortlist/](endpoints/agency/candidates.md) — Shortlist a candidate (authenticated)
- [POST /api/v1/agency/candidates/<id>/meeting/](endpoints/agency/candidates.md) — Create Zoom meeting and invite candidate (authenticated)
- [POST /api/v1/agency/candidates/<id>/offer/](endpoints/agency/candidates.md) — Send offer and create placement (authenticated)
- [POST /api/v1/agency/candidates/<id>/accept/](endpoints/agency/candidates.md) — Set candidate status to accepted (authenticated)
- [POST /api/v1/agency/candidates/<id>/reject/](endpoints/agency/candidates.md) — Set candidate status to rejected (authenticated)
- [POST /api/v1/agency/candidates/public/upload-cv/](endpoints/agency/candidates.md) — Public endpoint to upload a CV/resume (public)
- [GET  /api/v1/agency/interviews/](endpoints/agency/interviews.md) — List agency interviews with pagination, status filters, search, and summary metrics (authenticated)
- [GET  /api/v1/agency/interviews/calendar/](endpoints/agency/interviews.md) — List agency interviews for a specific month/year, only containing date time, candidate name, and position (authenticated)
- [GET  /api/v1/agency/placements/](endpoints/agency/placements.md) — List placements with pagination, filters, and status counts (authenticated)


---

### Integrations

- [GET  /api/v1/integrations/](endpoints/integrations.md) — List all integrations for the authenticated user (authenticated)
- [GET  /api/v1/integrations/zoom/connect/](endpoints/integrations.md) — Generate the Zoom OAuth authorization URL (authenticated)
- [GET  /api/v1/integrations/zoom/callback/](endpoints/integrations.md) — OAuth callback endpoint that Zoom redirects to after user authorization
- [POST /api/v1/integrations/zoom/disconnect/](endpoints/integrations.md) — Disconnect the user's Zoom integration (authenticated)
- [POST /api/v1/integrations/zoom/meetings/create/](endpoints/integrations.md) — Create a scheduled Zoom meeting (authenticated)

---

### Finance

- [POST /api/v1/finance/clients/<id>/revenue/](endpoints/finance.md) — Record client revenue (authenticated)

---

### Main

- [POST /api/v1/main/contact/](endpoints/main.md) — Post/create a contact message (public)
- [GET  /api/v1/main/search/](endpoints/main.md) — Search dashboard data across leads, candidates, clients, and jobs (authenticated)

---

Add other apps here as their endpoint pages are created under `docs/endpoints/`.


