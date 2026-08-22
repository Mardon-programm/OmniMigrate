# API Reference

Base URL: `http://localhost:8000/api/v1`

All authenticated endpoints require `Authorization: Bearer <access_token>`.

---

## Auth

### POST /auth/register
Create a new user account.

```json
{"email": "user@example.com", "password": "string", "full_name": "string"}
```
Response: `{access_token, refresh_token, token_type, user: {...}}`

### POST /auth/login
Authenticate and get tokens.

```json
{"email": "user@example.com", "password": "string"}
```
Response: `{access_token, refresh_token, token_type, user: {...}}`

### POST /auth/refresh
Refresh an access token.

```json
{"refresh_token": "string"}
```
Response: `{access_token, refresh_token, token_type}`

### POST /auth/logout
Block the refresh token (server-side).

```json
{"refresh_token": "string"}
```

### POST /auth/forgot-password
Request a password reset link. Always returns 200 (prevents email enumeration).

```json
{"email": "user@example.com"}
```

### POST /auth/reset-password
Reset password with a valid token.

```json
{"token": "string", "new_password": "string"}
```

---

## Users

### GET /users/me
Get current user profile.

### GET /users
List all users (admin only).

### POST /users
Create a user (admin only).

### PATCH /users/{id}
Update a user (admin only).

### POST /users/{id}/password
Change a user's password (admin only).

---

## Projects

### GET /projects
List projects for the current user.

### POST /projects
Create a new project.

### GET /projects/{id}
Get project details.

### PATCH /projects/{id}
Update a project.

### DELETE /projects/{id}
Delete a project and all its jobs.

---

## Jobs

### GET /jobs
List migration jobs.

### POST /jobs
Submit a new migration job.

### GET /jobs/{id}
Get job details.

### GET /jobs/{id}/status
Get real-time job status from Redis.

### GET /jobs/{id}/diff
Get the migration diff.

### GET /jobs/{id}/output
Get the migration output code.

### DELETE /jobs/{id}
Cancel a job.

---

## Migrations

### POST /migrations/analyze
Run AST analysis on source code.

```json
{"code": "python source", "filename": "main.py"}
```
Response: `{success, findings: [...], parse_error}`

### POST /migrations/preview-diff
Preview a unified diff between two code versions.

### GET /migrations/health
Check migration engine health.

---

## Autonomous Migration

### POST /autonomous/run
Start a full autonomous Git migration pipeline.

```json
{"repo_url": "https://github.com/org/repo", "github_token": "optional", "base_branch": "main"}
```

### GET /autonomous/jobs/{id}
Get autonomous job status and results.

---

## Organizations

### POST /organizations
Create an organization.

### GET /organizations/{id}
Get organization details.

### GET /organizations/{id}/members
List members.

### POST /organizations/{id}/members
Add a member.

### PATCH /organizations/{id}/members/{member_id}
Update member role/status.

### DELETE /organizations/{id}/members/{member_id}
Remove a member.

### GET /organizations/{id}/audit-logs
List audit log entries.

---

## Billing

### GET /billing/plans
List available plans.

### GET /billing/organizations/{id}/subscription
Get org subscription.

### GET /billing/organizations/{id}/usage
Get raw usage counts (jobs, llm_tokens, files).

### GET /billing/organizations/{id/dashboard
Usage dashboard: per-metric usage, quotas, percentages, and daily history.

### POST /billing/organizations/{id}/checkout
Create a Stripe checkout session.

### POST /billing/webhook/stripe
Handle Stripe webhooks.

---

## System

### GET /
Root info (app name, version, docs URL).

### GET /healthz
Liveness probe. Always returns `{status: "ok"}`.

### GET /readyz
Readiness probe. Checks Redis + DB connectivity.
Returns 200 if healthy, 503 if degraded.

### GET /metrics
Prometheus metrics (counters, histograms, gauges).

---

## Error Format

All errors return:

```json
{
  "detail": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "errors": []
}
```

Standard codes: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `INTERNAL_ERROR`, `RATE_LIMITED`.
