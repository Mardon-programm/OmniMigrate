# Contributing to OmniMigrate

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 22+
- Docker & Docker Compose

### Getting Started

```bash
# Clone the repository
git clone https://github.com/your-org/omnimigrate.git
cd omnimigrate

# Start the development environment
docker compose up -d

# Backend (in a separate terminal)
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests (hermetic — no Docker needed)
cd backend
.venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-fail-under=85

# Frontend tests
cd frontend
npm run test
```

### Code Quality

Pre-commit hooks run automatically on `git commit`:

```bash
# Manual checks
cd backend
ruff check app tests
ruff format --check app tests
pyright app tests

cd frontend
npm run build  # includes tsc --noEmit
npm run test
```

## Architecture

```
backend/
  app/
    api/v1/       — FastAPI route modules (one file per resource)
    core/         — Config, database, deps, rate limiting, security
    models/       — SQLAlchemy 2.0 async models
    schemas/      — Pydantic v2 request/response schemas
    services/     — Business logic (AST, LLM, sandbox, orchestrator)
  tests/          — pytest + aiosqlite (hermetic, no Docker)
  alembic/        — Database migrations

frontend/
  src/
    components/   — Reusable UI components (Modal, StatusBadge, etc.)
    context/      — React contexts (Auth, Toast)
    i18n/         — Internationalization (EN + RU)
    pages/        — Route-level page components
    services/     — Axios API client
    types/        — TypeScript interfaces
```

## Branch Strategy

1. Create a feature branch from `main`
2. Make changes with tests
3. Ensure CI passes (lint, typecheck, tests, coverage)
4. Open a PR using the PR template
5. Get at least one review

## Commit Convention

Use conventional commits:
- `feat: add billing webhook handler`
- `fix: correct SSRF check for IPv6`
- `test: add billing service tests`
- `docs: update API reference`

## PR Requirements

- [ ] Tests pass (`pytest --cov-fail-under=85` / `vitest run`)
- [ ] Linting passes (`ruff check` / `tsc --noEmit`)
- [ ] No secrets in code (detected by pre-commit hooks)
- [ ] New features include tests
- [ ] Documentation updated if applicable

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
