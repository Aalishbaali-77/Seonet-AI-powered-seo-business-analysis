# SIPulse

**SIPulse — AI-Powered Business Growth Intelligence Platform**  
Owned by **SI Global Solutions**

SIPulse combines website intelligence (SEO, AEO, GEO, performance, accessibility), lead intelligence (ICP, geo discovery, enrichment, scoring), and CRM automation (native, HubSpot, Odoo) in one multi-tenant SaaS.

This repository is the production-oriented foundation. Incomplete modules are feature-flagged; they are not mocked as live data.

## Architecture

Modular Django API + Celery workers + Next.js / MUI client. PostgreSQL, Redis, RabbitMQ. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features (by phase)

| Area | Status |
| --- | --- |
| Auth, tenants, RBAC, audit log | Phase 2 |
| App shell, dashboard | Phase 3 |
| Website audit / crawler | Phase 4 |
| AI gateway | Phase 5 |
| Lead intelligence | Phase 6 |
| Native CRM | Phase 7 |
| HubSpot / Odoo | Phase 8 |
| Billing / usage | Phase 9 |
| Reports | Phase 10 |

## Requirements

- Python 3.11+
- Node.js 20+ (24 is fine)
- Docker (recommended) or local PostgreSQL 16, Redis, RabbitMQ
- npm (this frontend uses npm, not pnpm/yarn)

## Local setup

```bash
copy .env.example .env
```

Edit `.env`. Then either:

### Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000  
- API: http://localhost:8000  
- OpenAPI: http://localhost:8000/api/docs/

### Manual

```bash
# backend
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
cd backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# worker (Windows: solo pool)
celery -A config.celery worker -l INFO --pool=solo

# frontend
cd frontend
npm install
npm run dev
```

## Environment variables

See `.env.example`. Never put provider secrets in `NEXT_PUBLIC_*` variables.

## Database

PostgreSQL via `DATABASE_URL`. Apply migrations with `python manage.py migrate`. Development seed: `python manage.py seed_demo` (not for production).

## Tests

```bash
cd backend
pytest
cd ..\frontend
npm run test
npm run lint
```

## Production

Gunicorn + Celery + `next start`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

| Doc | Contents |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Phased roadmap |
| [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) | Schema |
| [docs/API_DESIGN.md](docs/API_DESIGN.md) | HTTP API |
| [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) | UI structure |
| [docs/SECURITY.md](docs/SECURITY.md) | Authz, SSRF, secrets |
| [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | AI gateway |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Providers |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Tests |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Run / deploy |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADRs |
