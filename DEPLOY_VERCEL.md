# Vercel Deployment Guide for OmniMigrate

## ⚠️ Critical Limitation

**Vercel does NOT support:**
- Long-running Python processes (workers, arq)
- Persistent connections (Redis, PostgreSQL)
- Background jobs > 30s (max 60s on Pro)
- File system persistence (`/data/workspaces`)

## Architecture Adaptation Required

```
┌─────────────────────────────────────────────────────────────┐
│                    VERCEL DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vercel)     │  Backend (Vercel Functions)       │
│  - Static build        │  - FastAPI → Serverless functions │
│  - Edge caching        │  - Max 60s execution              │
└────────────────────────┴────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ PostgreSQL│     │  Redis   │     │  Worker  │
    │ (Neon/    │     │ (Upstash/│     │ (Railway/│
    │  Supabase)│     │  Redis    │     │  Render)│
    └─────────┘       └─────────┘       └─────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                    EXTERNAL SERVICES
```

## Step 1: External Services (Required Before Deploy)

### PostgreSQL → Neon (Recommended)
```bash
# 1. Create project at https://neon.tech
# 2. Get connection string
# 3. Add to Vercel env: DATABASE_URL
# Format: postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
```

### Redis → Upstash (Recommended)
```bash
# 1. Create database at https://upstash.com
# 2. Get REST URL + Token
# 3. Add to Vercel env:
#    REDIS_URL=redis://default:token@host:port
#    UPSTASH_REDIS_REST_URL=https://...
#    UPSTASH_REDIS_REST_TOKEN=...
```

### Background Workers → Railway / Render
```bash
# Deploy worker separately:
# 1. Connect GitHub repo to Railway
# 2. Set env vars (same as backend)
# 3. Command: python -m app.worker_runner
# 4. Cost: ~$5/mo for hobby
```

## Step 2: Vercel Project Setup

### Frontend (Auto-detected)
```json
// vercel.json already configured correctly
{
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}
```

### Backend (Needs Adaptation)

**Problem:** `backend/vercel.json` uses `api/index.py` but current structure has FastAPI in `app/main.py`

**Fix:** Create `/backend/api/index.py`:
```python
# backend/api/index.py
from app.main import app
```

**Update `backend/vercel.json`:**
```json
{
  "buildCommand": "pip install -r requirements.txt",
  "installCommand": "pip install -r requirements.txt",
  "functions": {
    "api/index.py": {
      "runtime": "python3.12",
      "maxDuration": 60
    }
  }
}
```

## Step 3: Environment Variables (Vercel Dashboard)

Go to **Project → Settings → Environment Variables** and add:

| Variable | Value | Environment |
|----------|-------|-------------|
| `SECRET_KEY` | `openssl rand -hex 32` | All |
| `DATABASE_URL` | `postgresql://...` (Neon) | All |
| `REDIS_URL` | `redis://...` (Upstash) | All |
| `OPENAI_API_KEY` | `sk-...` or Groq key | All |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` (if Groq) | All |
| `OPENAI_MODEL` | `gpt-4o-mini` or `llama-3.1-70b-versatile` | All |
| `ALLOWED_ORIGINS` | `["https://your-domain.vercel.app"]` | All |
| `STRIPE_SECRET_KEY` | `sk_live_...` | Production |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | Production |
| `SMTP_HOST` | `smtp.resend.com` | All |
| `SMTP_PORT` | `587` | All |
| `SMTP_USER` | `resend` | All |
| `SMTP_PASSWORD` | `re_...` (Resend API key) | All |
| `SMTP_FROM_EMAIL` | `noreply@yourdomain.com` | All |
| `ENVIRONMENT` | `production` | Production |
| `DEBUG` | `false` | Production |

## Step 4: Database Migrations

**Option A: Run locally before deploy**
```bash
cd backend
DATABASE_URL="your-neon-url" alembic upgrade head
```

**Option B: GitHub Action (auto on deploy)**
```yaml
# .github/workflows/deploy.yml
- name: Run migrations
  run: |
    cd backend
    pip install -r requirements.txt
    alembic upgrade head
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

## Step 5: Stripe Webhook Configuration

1. Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-app.vercel.app/api/v1/billing/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy signing secret → `STRIPE_WEBHOOK_SECRET`

## Step 6: Domain & SSL

```bash
# 1. Add domain in Vercel Project → Settings → Domains
# 2. Vercel auto-provisions Let's Encrypt SSL
# 3. Update ALLOWED_ORIGINS with your domain
# 4. Update Stripe webhook URL to production domain
```

## Step 7: Required Code Changes for Vercel

### 1. Fix Redis for Serverless (Upstash REST)
```python
# app/core/database.py - add Upstash client
import os
import httpx

class UpstashRedis:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    
    async def ping(self):
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.url}/ping", headers={"Authorization": f"Bearer {self.token}"})
            return r.json().get("result") == "PONG"
    
    async def get(self, key):
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.url}/get/{key}", headers={"Authorization": f"Bearer {self.token}"})
            return r.json().get("result")
    
    async def set(self, key, value, ex=None):
        # ... implement
        pass
```

### 2. Remove Background Worker Dependencies
```python
# In main.py lifespan - REMOVE worker startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # REMOVE: app.state.redis = await get_redis()  # Use Upstash instead
    yield
```

### 3. Handle Long-Running Migrations
```python
# For migrations > 60s, use async pattern:
# 1. POST /jobs returns job_id immediately
# 2. Frontend polls /jobs/{id}/status
# 3. Worker on Railway does actual work
```

## Step 8: Deploy Commands

```bash
# Frontend
cd frontend && npm run build
vercel --prod

# Backend
cd backend
vercel --prod

# Or use Vercel GitHub integration (auto-deploy on push)
```

## Cost Estimate (Monthly)

| Service | Hobby/Start | Production |
|---------|-------------|------------|
| Vercel (Frontend) | $0 | $20 (Pro) |
| Vercel (Backend Functions) | $0 | $20 (Pro) |
| Neon PostgreSQL | $0 | $19 (Scale) |
| Upstash Redis | $0 | $0.50/100k req |
| Railway Worker | $5 | $20 |
| Stripe | 2.9% + 30¢ | 2.9% + 30¢ |
| Resend Email | $0 (3k/mo) | $20 |
| **Total** | **~$5** | **~$100** |

## Checklist Before Launch

- [ ] Neon PostgreSQL created, `DATABASE_URL` in Vercel
- [ ] Upstash Redis created, credentials in Vercel
- [ ] Railway worker deployed and healthy
- [ ] `SECRET_KEY` generated (32+ chars)
- [ ] `OPENAI_API_KEY` or Groq configured
- [ ] Stripe live keys + webhook configured
- [ ] Resend SMTP verified + domain authenticated
- [ ] Custom domain added in Vercel + SSL active
- [ ] `ALLOWED_ORIGINS` updated to production domain
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Test: Register → Create Project → Submit Migration → View Diff
- [ ] Test: Stripe checkout flow
- [ ] Test: Password reset email
- [ ] Sentry DSN added (`VITE_SENTRY_DSN`)
- [ ] PostHog key added (`VITE_POSTHOG_KEY`)

## Known Issues on Vercel

| Issue | Workaround |
|-------|------------|
| 60s function timeout | Offload long tasks to Railway worker |
| No persistent `/data` | Use S3/R2 for file storage |
| Cold starts (~1-3s) | Enable Vercel Pro for warm instances |
| No WebSocket support | Use Server-Sent Events or polling |
| Body size limit 4.5MB | Upload large files to S3 directly |

## Alternative: Full VPS (Simpler for Python)

If Vercel limitations are blocking, deploy everything to **Hetzner CX22 (€4.50/mo)** or **DigitalOcean Droplet ($6/mo)** using `docker-compose.prod.yml` — no architecture changes needed.

---

**Recommendation:** Start with Vercel for frontend + Neon + Upstash + Railway worker. Move to VPS when you hit limits or need WebSockets/persistent storage.