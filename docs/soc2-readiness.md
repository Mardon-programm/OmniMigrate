# SOC 2 Readiness Checklist

OmniMigrate targets **SOC 2 Type II** compliance. This document tracks readiness across the Trust Service Criteria.

---

## 1. Security (CC6)

| Control | Status | Evidence |
|---------|--------|----------|
| Access controls per user role | Done | RBAC model: admin/engineer/client per org |
| Password hashing (bcrypt) | Done | bcrypt with configurable rounds (>=12) |
| JWT token expiry + refresh | Done | 24h access, 7d refresh, Redis blocklist |
| Token encryption at rest | Done | Fernet + SHA-256 derived key for GitHub tokens |
| Secrets never in DB/Redis plaintext | Done | All tokens encrypted before storage |
| Network security (SSRF prevention) | Done | DNS allowlist, RFC1918 blocking, IP validation |
| Container isolation (sandbox) | Done | RLIMIT_AS, RLIMIT_CPU, no core dumps |
| Rate limiting (global + per-org) | Done | Redis-based, configurable per-tenant |
| Audit logging | Done | Who/what/when on all sensitive operations |
| Structured logging | Done | structlog with JSON output |
| Observability (tracing) | Done | OpenTelemetry + Prometheus metrics |
| Authentication with MFA | Pending | SSO/SAML (Phase 1) |

## 2. Availability (A1)

| Control | Status | Evidence |
|---------|--------|----------|
| Health checks | Done | /healthz (liveness), /readyz (readiness) |
| Graceful degradation | Done | LLM -> local deterministic rules fallback |
| Redis failure tolerance | Done | Redis errors logged, pipeline continues |
| Load testing | Done | k6 scripts: smoke, load (50 VU), stress (200 VU) |
| Structured error responses | Done | Consistent JSON error format with codes |

## 3. Processing Integrity (PI1)

| Control | Status | Evidence |
|---------|--------|----------|
| Input validation | Done | Pydantic schemas, FastAPI validation |
| Automated test suite | Done | 330+ tests, CI gates merge |
| Sandbox verification | Done | Every output verified in isolation |
| Self-healing loop | Done | Up to 3 repair attempts per migration |
| Diff-based change review | Done | Unified diff + metrics for every job |

## 4. Confidentiality (C1)

| Control | Status | Evidence |
|---------|--------|----------|
| Data isolation per org | Done | Organization-scoped queries |
| Role-based access | Done | RBAC: owner/admin/member/viewer |
| Audit trail | Done | Full audit log per organization |
| Token blocklist on logout | Done | Redis-backed refresh token blocklist |

## 5. Privacy (P1)

| Control | Status | Evidence |
|---------|--------|----------|
| Minimal data collection | Done | Only email, name, hashed password |
| No PII in logs | Done | structlog processors exclude secrets |
| Data retention | Pending | Configurable TTL for job data |

## Remaining Items

- [ ] SSO/SAML + MFA integration
- [ ] SCIM provisioning from corporate IdP
- [ ] DR playbook and backup automation
- [ ] Security policy documentation
- [ ] Access review process
- [ ] Data retention policies
