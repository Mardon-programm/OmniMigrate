# OmniMigrate

**Enterprise-grade, autonomous AI-powered code migration and modernization engine.**

OmniMigrate reads legacy source code, parses it via AST (LibCST), analyzes patterns
(deprecated imports, Python 2 constructs, security issues, N+1 patterns), runs an
LLM refactoring pipeline with a **self-healing sandbox loop**, and produces clean
modern code with a unified diff report.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (Async), Pydantic v2, Alembic, LibCST, OpenAI SDK, arq + Redis
- **Database / Cache:** PostgreSQL 15, Redis 7
- **Frontend:** React 18 + TypeScript, Tailwind CSS, Lucide Icons, Axios, Vite
- **Infrastructure:** Docker Compose, Nginx reverse proxy

## Quick start (Docker)

Prerequisites: Docker Engine with Compose v2.

```bash
# 1. Configure secrets
cp backend/.env.example backend/.env
#    Edit backend/.env and set a strong SECRET_KEY and your OPENAI_API_KEY.

# 2. Boot the entire stack (PostgreSQL + Redis + backend + worker + frontend)
docker compose up --build
```

- Frontend (Nginx): http://localhost
- Backend API: http://localhost:8003
- Swagger docs: http://localhost:8003/api/docs
- Health check: http://localhost:8003/healthz

Database migrations run automatically on backend startup (`alembic upgrade head`).

### First steps

1. Open http://localhost and **register** a Client account.
2. Create a project (e.g. source `python` → target `python-3.12`).
3. Open **New Migration**, paste legacy code, run **AST analysis**, then submit.
4. Watch live progress, inspect findings, and review the generated diff.

> To create an **admin** account, run against the running Postgres container:
> ```bash
> docker compose exec postgres psql -U omnimigrate -d omnimigrate \
>   -c "UPDATE users SET role='admin' WHERE email='you@company.com';"
> ```

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL must be running. Point DATABASE_URL at it in backend/.env.
alembic upgrade head             # initialize schema
uvicorn app.main:app --reload
```

Run the task worker in a second terminal:

```bash
arq app.core.worker.WorkerSettings
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173 (proxies /api -> :8003)
```

## Configuration

All backend settings live in `backend/.env` (see `backend/.env.example`):

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | Async PostgreSQL connection string |
| `REDIS_URL` | Redis connection for the task queue and job state |
| `OPENAI_API_KEY` | LLM provider key for the refactoring engine |
| `OPENAI_MODEL` | e.g. `gpt-4o-mini` |
| `SANDBOX_ENABLED` | Execute migrated code in an isolated subprocess during verification |
| `MAX_SELF_HEAL_ATTEMPTS` | Max LLM repair rounds before a job is marked failed |

## Architecture

```
Routers (FastAPI)  ->  Services (AST Parser / LLM Agent / Sandbox / Engine)
        |                        |
        v                        v
   Repositories            arq worker (Redis queue)
        |                        |
        v                        |
  SQLAlchemy models             |
        |________________________|
   PostgreSQL + Redis state
```

Migration pipeline per job:

1. **Parsing** – LibCST walks the AST, collecting findings (deprecated imports, `datetime.utcnow`, `xrange`, `== None`, hardcoded secrets, N+1 hints…).
2. **Analyzing** – findings are rendered into the strict engine prompt.
3. **Refactoring** – LLM returns raw code only (zero filler; signatures preserved).
4. **Verifying** – sandbox `compile()` + isolated subprocess run.
5. **Self-healing** – failed output is fed back to the LLM with the sandbox error (up to `MAX_SELF_HEAL_ATTEMPTS`).
6. **Completed** – unified diff + metrics stored; status streamed via Redis for the live UI.

## Testing

```bash
cd backend && pytest                # unit tests: AST parser, sandbox, security, diff
cd frontend && npm run test         # vitest: diff parser
cd frontend && npm run build        # type-safe production build
```

## API overview

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Register (client) |
| POST | `/api/v1/auth/login` | Login → JWT access/refresh |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Current user |
| GET/POST/PATCH/DELETE | `/api/v1/projects` | Manage projects |
| POST | `/api/v1/jobs` | Submit a migration job (enqueues worker) |
| GET | `/api/v1/jobs/{id}` | Full job detail |
| GET | `/api/v1/jobs/{id}/status` | Live status (Redis-backed progress) |
| GET | `/api/v1/jobs/{id}/diff` | Generated unified diff |
| GET | `/api/v1/jobs/{id}/output` | Refactored code |
| POST | `/api/v1/migrations/analyze` | Dry-run AST analysis |
| POST | `/api/v1/migrations/preview-diff` | Preview diff between snippets |
