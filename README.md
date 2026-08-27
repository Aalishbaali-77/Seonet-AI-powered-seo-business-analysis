# Seonet

**AI-powered SEO & business intelligence platform**, delivered as a multi-tenant SaaS.

Seonet audits websites (SEO, AEO, performance, accessibility), turns that intelligence into leads and market insight, and pushes qualified opportunities into a built-in CRM or an external one (HubSpot, Odoo) — all from one workspace.

> Incomplete modules are feature-flagged behind environment variables rather than shipped as mocked/fake data. See [Feature flags](#feature-flags).

## What it does

| Capability | Summary |
| --- | --- |
| **Website audits** | Crawls a site, scores SEO/AEO/performance/accessibility, and produces issues + AI-generated fix recommendations. Includes keyword rank tracking and automated fix runs. |
| **Lead intelligence** | Define an Ideal Customer Profile (ICP), run geo-based lead discovery/enrichment, and manage results as lead lists. |
| **Market intelligence** | Geo/market signal tracking and scoring to surface business opportunities in a target area. |
| **CRM** | Native pipeline/stage/deal/contact/company CRM, or sync with HubSpot / Odoo / Google Sheets via the integrations layer. |
| **Business & commerce insight** | Business profiles, catalog/order/review data ingestion (with import batches + duplicate prevention) for e-commerce/business analysis. |
| **AI advisor** | Prompt-driven "Ask AI" assistant and advisory panels backed by Anthropic Claude, OpenAI, or xAI, with usage/credit tracking. |
| **Billing & usage** | Plans, product modules, subscriptions, invoices, and usage metering, with Stripe/PayPal gateway support. |
| **Control plane** | Platform-owner admin console: tenant management, module/package/subscription control, lead-source config, white-label appearance/branding, landing page content. |
| **Multi-tenancy & RBAC** | Tenants, teams, memberships, and a permission/role system enforced across every tenant-owned resource. |

## Architecture

- **Backend**: Django 5 + Django REST Framework, JWT auth (`djangorestframework-simplejwt`), OpenAPI schema via drf-spectacular.
- **Async work**: Celery, broker = RabbitMQ, result backend = Redis. A separate `beat` service runs scheduled tasks (audits, keyword rank runs, fix runs, lead discovery, etc.).
- **Database**: PostgreSQL (SQLite fallback for quick local runs).
- **Frontend**: Next.js 16 (App Router) + React 19, MUI, Redux Toolkit + redux-saga, react-hook-form + zod, Tailwind for utility styling.
- **Multi-tenancy**: every tenant-owned model is scoped through shared base models/managers in `apps/common`, with `apps/tenants` and `apps/rbac` enforcing membership and permissions.

### Backend apps (`backend/apps/`)

| App | Responsibility |
| --- | --- |
| `tenants` | Tenants, memberships, teams — the multi-tenancy core. |
| `rbac` | Roles, permissions, role-permission and membership-role mapping. |
| `users` | Custom user model and auth. |
| `websites` | Tenant websites, website access, audit-fix runs, keyword rank runs. |
| `crawler` | Crawling primitives (fetcher, parser, SSRF guard, metrics) used by `audits`. |
| `audits` | Crawl results, audits, audit issues, and recommendations. |
| `leads` | ICPs, lead searches, lead lists, and leads. |
| `markets` | Geo places, scoring profiles, market focus and signals. |
| `opportunities` | Sales/business opportunities surfaced from audits, leads, and markets. |
| `business` | Business profiles and commerce data: catalog products, customers, orders, reviews, import batches. |
| `crm` | Pipelines, stages, companies, contacts, deals, activities. |
| `integrations` | External CRM connections (HubSpot, Odoo, Google Sheets, webhooks), field mapping, tenant API tokens. |
| `marketing` | Marketing campaigns. |
| `ai` | AI prompt templates/versions and request/usage logging for LLM calls. |
| `billing` | Product modules, plans, tenant modules, payment gateways, subscriptions, invoices. |
| `usage` | Usage metering records. |
| `jobs` | Generic async job/progress tracking for Celery-driven work. |
| `notifications` | Tenant notifications. |
| `auditlog` | Audit trail and website page-view telemetry. |
| `platform` | Platform-owner (control-plane) admin config: appearance, landing page, lead sources. |
| `core` | Cross-module dashboard overview and workspace report aggregation. |
| `api` | Root URL router wiring every app's endpoints under `/api/v1/`. |
| `common` | Shared abstract base models (UUID PK, timestamps, soft delete) and tenant-scoped querysets. |

### Frontend features (`frontend/src/features/`)

`auth`, `dashboard`, `websites` (audits, issues, keyword tracking, fix runs), `growth` (AI advisor, business/market/opportunity views, commerce insight, market heatmap), `leads`, `crm`, `marketing` (public site), `integrations`, `billing`, `jobs`, `settings` (API keys, workspace, profile), `platform` (tenant usage/integrations overview), `controlPlane` (platform-admin console), `docs` (in-app documentation).

## Requirements

- Python 3.11+
- Node.js 20+ (24 is fine) — this frontend uses npm, not pnpm/yarn
- Docker (recommended) or local PostgreSQL 16, Redis, and RabbitMQ

## Local setup

```bash
copy .env.example .env
```

Fill in `.env` — see [Environment variables](#environment-variables). At minimum you need `DJANGO_SECRET_KEY`; everything else has sane local defaults or is behind a feature flag.

### Option A — Docker

```bash
docker compose up --build
```

Spins up Postgres, Redis, RabbitMQ, the Django API, a Celery worker, Celery beat, and the Next.js frontend.

- Frontend: <http://localhost:3000>
- API: <http://localhost:8000>
- OpenAPI schema/docs: <http://localhost:8000/api/docs/>

### Option B — Manual

```bash
# backend
.venv\Scripts\activate
pip install -r backend\requirements.txt
cd backend
python manage.py migrate
python manage.py seed_demo   # optional local seed data — not for production
python manage.py runserver

# Celery worker (separate shell; Windows needs the solo pool)
celery -A config.celery worker -l INFO --pool=solo

# Celery beat, for scheduled tasks (separate shell)
celery -A config.celery beat -l INFO

# frontend (separate shell)
cd frontend
npm install
npm run dev
```

`run.bat` is a Windows convenience script that starts the backend dev server and frontend in separate terminal windows (assumes a `.venv` already exists and Docker services — Postgres/Redis/RabbitMQ — are running separately).

## Environment variables

See `.env.example` for the full list. Never put provider secrets in `NEXT_PUBLIC_*` variables — those are shipped to the browser.

| Category | Variables |
| --- | --- |
| Django core | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ENV`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` |
| Database / queue / cache | `DATABASE_URL`, `REDIS_URL`, `RABBITMQ_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Auth / CORS | `AUTH_COOKIE_DOMAIN`, `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE`, `CORS_ALLOWED_ORIGINS` |
| Email | `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL` |
| Observability | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `OTEL_EXPORTER_OTLP_ENDPOINT` |
| AI providers | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `AI_AEO_ENABLED` |
| CRM integrations | `HUBSPOT_CLIENT_ID` / `_SECRET` / `_ENABLED`, `ODOO_URL` / `_DATABASE` / `_CLIENT_ID` / `_SECRET` / `_ENABLED` |
| Lead discovery & enrichment | `APOLLO_API_KEY`, `CLEARBIT_API_KEY`, `HUNTER_API_KEY`, `OPENCORPORATES_API_TOKEN`, `SERPAPI_API_KEY`, `YELP_API_KEY`, `FOURSQUARE_API_KEY`, `GEOAPIFY_API_KEY`, `NOMINATIM_CONTACT_EMAIL`, `LINKEDIN_ACCESS_TOKEN`, `LEAD_DISCOVERY_ENABLED` |
| Google services | `GOOGLE_MAPS_API_KEY`, `GOOGLE_PLACES_API_KEY`, `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CSE_ID` |
| Frontend URLs | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL`, `PUBLIC_APP_URL` |
| Misc | `WHITE_LABEL_ENABLED` |

### Feature flags

Modules that depend on paid third-party APIs are gated so the app runs cleanly without every key configured:

- `HUBSPOT_ENABLED`, `ODOO_ENABLED` — external CRM sync
- `AI_AEO_ENABLED` — AI-driven Answer Engine Optimization scoring
- `LEAD_DISCOVERY_ENABLED` — lead discovery/enrichment providers
- `WHITE_LABEL_ENABLED` — control-plane branding/appearance overrides

## Database

PostgreSQL via `DATABASE_URL` (falls back to SQLite for quick local runs). Apply migrations with `python manage.py migrate`. `python manage.py seed_demo` loads development seed data — do not run it against production.

## Tests

```bash
cd backend
pytest
```

Backend test coverage is currently minimal (a handful of apps have placeholder `tests.py` files) and there is no automated frontend test suite yet — treat both as an open contribution area rather than a safety net.

## Production

Run Django behind Gunicorn, Celery worker + beat as long-running services, and `next build && next start` for the frontend. Reuse the same environment variables as local setup, with `DJANGO_DEBUG=false`, real `DJANGO_ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`, and a managed Postgres/Redis/RabbitMQ instead of the Docker Compose services.

## Project structure

```text
backend/    Django project (apps/, config/, manage.py)
frontend/   Next.js app (src/app, src/features, src/components, src/store)
docker/     Dockerfiles for backend and frontend
docker-compose.yml   Local dev stack: postgres, redis, rabbitmq, backend, worker, beat, frontend
```
