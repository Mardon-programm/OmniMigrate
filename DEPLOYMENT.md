# OmniMigrate Production Deployment Guide

## 🎯 Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │    Render       │
│  (Frontend)     │────▶│  (Backend)      │
│  Next.js/Vite   │     │  FastAPI        │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┴────────┐
                    ▼                     ▼
              ┌──────────┐          ┌──────────┐
              │ PostgreSQL │         │   Redis   │
              │  (Neon/    │         │ (Upstash/ │
              │  Supabase/  │         │  Render)  │
              │  Render)    │         └──────────┘
              └──────────┘
```

## 🚀 Quick Start

### 1. Prerequisites
- GitHub repo connected to Vercel & Render
- **Paid** Gemini API key (the free tier's 20 req/day quota is not viable for pilots; it already caused wasted proof runs)
- Paddle account (billing)
- Resend/SendGrid (email)
- PostgreSQL (Neon/Supabase/Render)
- Redis (Upstash/Render)

### 2. Environment Variables

**Backend (.env.prod)** - Set in Render dashboard
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/omnimigrate
REDIS_URL=redis://host:6379/0
OPENAI_API_KEY=your-gemini-key
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_MODEL=gemini-2.5-flash
# Real random value, >=32 chars; placeholders are rejected at startup.
SECRET_KEY=<openssl rand -hex 32>
DEBUG=false
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app"]

# Anti-shrinkage output contract — keep enabled in production.
CONTRACT_ENABLED=true
CONTRACT_MIN_LINE_RATIO=0.75

LLM_MAX_TOKENS=65536
LLM_FALLBACK_TO_RULES=true

PADDLE_API_KEY=live_...
PADDLE_VENDOR_ID=...
PADDLE_WEBHOOK_SECRET=live_...
PADDLE_PRICE_STARTER_MONTHLY=pri_...
PADDLE_PRICE_PRO_MONTHLY=pri_...
PADDLE_PRICE_PACK_10=pri_...
PADDLE_PRICE_PACK_50=pri_...
PADDLE_PRICE_PACK_100=pri_...
PADDLE_PRICE_PACK_500=pri_...
PADDLE_PRICE_PACK_1000=pri_...
SMTP_HOST=smtp.resend.com
SMTP_USER=resend
SMTP_PASSWORD=re_...
SMTP_FROM_EMAIL=noreply@yourdomain.com
SENTRY_DSN=
```

**Frontend** (Vercel Environment Variables)
```
VITE_API_URL=https://api.yourdomain.com
VITE_MARKETING_URL=https://yourdomain.com
```

### 3. Deploy

```bash
# Option 1: Vercel + Render (Recommended)
./deploy.sh vercel

# Option 2: VPS Self-hosted
./deploy.sh vps
```

Deployment notes:

- `render.yaml` runs `alembic upgrade heads` as `preDeployCommand`, so schema
  migrations are applied before the new backend process takes traffic. The VPS
  compose file does the same in the backend command before `uvicorn` starts.
- `.github/workflows/ci.yml` is the quality gate (ruff, format, pyright, tests).
  Its coverage threshold is the current measured baseline (65%); raise it as
  integration-heavy modules gain deterministic tests.
- `.github/workflows/deploy.yml` only triggers Render and Vercel deploy hooks.
  There is no GHCR image push — Render/Vercel build from the repository, so an
  extra registry was just a source of drift.
- Caddy is the only process bound to ports 80/443 on the VPS. The nginx
  frontend is exposed on the internal Docker network only.

### 4. Post-Deploy Checklist
- [ ] Health checks: `/healthz` on both services
- [ ] Test user registration/login
- [ ] Test migration job creation
- [ ] Configure a Paddle notification destination pointing to
  `POST /api/v1/billing/webhook` with `transaction.completed` and
  `subscription.*` events; copy its signing secret to `PADDLE_WEBHOOK_SECRET`
- [ ] Verify a simulated Paddle webhook is accepted and applied
- [ ] Test email delivery
- [ ] Configure custom domain + SSL
- [ ] Set up monitoring alerts

## 🔧 Key Files
- `render.yaml` - Render services (web + worker + DB + Redis), includes `preDeployCommand`
- `vercel.json` - Vercel configuration
- `docker-compose.prod.yml` - VPS self-hosting (migrations before uvicorn)
- `Caddyfile` - Public reverse proxy with auto-HTTPS; frontend stays internal
- `.github/workflows/ci.yml` - Quality gate: ruff, format, pyright, tests
- `.github/workflows/deploy.yml` - Render/Vercel deploy hooks only

## 📊 Monitoring
- **Sentry**: Error tracking (DSN in env)
- **PostHog**: Analytics (key in env)
- **Render/Neon dashboards**: DB/Redis metrics
- **Uptime**: UptimeRobot/Pingdom on `/healthz`

## 🚨 Troubleshooting

**Gemini 429 Rate Limit**: The free tier's 20 req/day is not enough for a real
migration. Use a paid Gemini key before running pilots. `gemini-flash-lite` can
be used for cheap smoke tests, but the Zope proof needed the 65,536-token
completion budget configured above.

**DB Connection Closed**: `pool_recycle=300` + `pool_pre_ping=True` in database.py

**Worker Not Processing**: Check Redis connection, queue names (`omnimigrate:urgent/normal/bulk`)

**CORS Errors**: Ensure `ALLOWED_ORIGINS` includes Vercel domain