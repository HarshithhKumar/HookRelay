# LinkPlease

LinkPlease — an Instagram comment-to-DM automation system for creators.

Turn keyword-triggered Instagram comments into reliable, idempotent DMs.

---

## 1. Assignment overview

This repository implements the LinkPlease tech-intern assignment: a service that accepts signed Instagram-style webhooks (the tested mock is PseudoGram), matches incoming comment events against user-defined rules, and sends DMs when a rule matches.

Reliability is a primary focus: the system is built to tolerate duplicate and out-of-order webhook deliveries, temporary network failures, and the mock API's rate limits. The PseudoGram mock intentionally introduces duplicates, out-of-order deliveries, transient failures, and rate limiting — the implementation documents how the system responds to these conditions.

---

## 2. Features (implemented)

Only features actually present in the codebase are listed.

### Core automation
- Keyword-based comment matching (case-insensitive substring match).
- DM job creation (DMJob) persisted to the database for durable processing.
- Rule creation via POST /rules.
- Background processing to send DMs and reconcile deliveries.

### Reliability
- Event-level deduplication (unique event_id enforced by the `events` table).
- Duplicate DM protection (database unique constraint on rule + recipient prevents duplicate DMJobs; duplicate-block records are written when a duplicate is detected).
- Stable idempotency keys for outbound sends (key format: `linkplease-dm-job-{job_id}`).
- Retry handling with exponential backoff and configurable max attempts.
- Rolling rate-limit enforcement (10 requests / 60 seconds window enforced via `dm_send_attempts` and a `DMRateLimitLock`).
- Persistent job state: DMJob, DMSendAttempt, Delivery, and duplicate-blocks are stored in the database so processing survives restarts.
- Delivery reconciliation: accepted sends (HTTP 202) are polled with GET /v1/dm/{dm_id} to observe final delivered/failed states.

### Webhook handling
- POST /webhook accepts signed webhook JSON and validates the signature using HMAC-SHA256 against the `PSEUDOGRAM_API_KEY`.
- Webhook JSON shape enforced by Pydantic schemas; invalid payloads are rejected with appropriate HTTP codes.
- Supported event types: `comment.created` (creates DMJobs if a rule matches). `comment.deleted` and unknown event types are intentionally no-ops (persisted, then marked processed).
- Incoming webhooks are acknowledged quickly; further processing is scheduled asynchronously.

### Monitoring
- `GET /health` — simple health check returning service and status.
- `GET /stats` — exposes exact counters required by assignment grading:
  - `sent`: confirmed delivered (Delivery.status == delivered)
  - `failed`: DMJobs in permanent FAILED state
  - `queued`: non-terminal DMJobs (queued, sending, accepted, retrying)
  - `duplicates_blocked`: durable duplicate-block records
- Frontend (React) provides a dashboard, rules UI, and a System Status page that queries `GET /stats` and `GET /health`.

---

## 3. How the system works (end-to-end)

Diagram (logical flow):

```
Instagram / PseudoGram
        ↓
POST /webhook  (signed HMAC-SHA256)
        ↓
Event persisted (events table) + deduplication via unique event_id
        ↓
Background processing (event_processor)
        ↓
Rule matching (case-insensitive substring)
        ↓
DMJob persisted (unique constraint on rule_id + recipient_user_id prevents duplicates)
        ↓
DM worker claims DMJob → reserves rate-limit slot → POST /v1/dm/send (Idempotency-Key = linkplease-dm-job-{job_id})
        ↓
If 202 accepted → DMJob marked ACCEPTED and Delivery row created
If 429 or transient error → job scheduled for retry with backoff
If 400 or permanent error → DMJob marked FAILED
        ↓
Reconciliation worker polls PseudoGram GET /v1/dm/{dm_id}
        ↓
Delivery updated to DELIVERED or FAILED; DMJob status updated accordingly
        ↓
GET /stats reports accurate counters derived from DB state
```

Each stage is implemented in the backend code under `backend/app/services` and the database models under `backend/app/models`.

---

## 4. Architecture

- Frontend: React + Vite (single-page app in `frontend/`).
- Backend: FastAPI application (`backend/app/`) exposing HTTP API endpoints.
- Database: SQLAlchemy models with Alembic migrations. Production `render.yaml` expects PostgreSQL, but the app supports a local SQLite fallback via `DATABASE_URL`.
- PseudoGram mock API: `https://pseudogram-api.onrender.com` (configured via `PSEUDOGRAM_BASE_URL`).
- Background workers: DM worker and Reconciliation worker. By default (Render "free" approach) the workers are started inside the FastAPI process on startup (see `app.main`), but helper functions allow running workers as a separate process if desired.

Notes:
- Worker threads are started on FastAPI startup unless `DISABLE_BACKGROUND_WORKERS` is set. This is intentional to allow a simple single-service deployment.

---

## 5. Backend API (reference)

Method | Endpoint | Purpose | Request | Response
---|---:|---|---|---
POST | /webhook | Accept a signed PseudoGram webhook. Response is quick acknowledgement. | JSON body matching schema: `{ "event_id": "...", "event_type": "comment.created", "sent_at": "2026-...", "data": { "comment_id": "...", "post_id": "...", "text": "...", "from": {"user_id":"...","username":"..."} } }`. Header `X-PseudoGram-Signature: sha256=<hex>` is required. | 200 OK: `{ "status": "accepted" }` or `{ "status": "duplicate" }`.
POST | /rules | Create a new automation rule. | JSON body: `{ "keyword": "price", "dm_message": "Thanks — here's our price..." }`. `keyword` is normalized to lowercase. | 201 Created: `{ "rule_id": "<uuid>", "keyword": "price", "dm_message": "..." }`.
GET | /rules | List active rules | No body | 200: `[{ "rule_id": "...", "keyword": "...", "dm_message": "..." }, ...]`.
GET | /rules/{rule_id} | Retrieve a rule by id | Path param | 200 rule object, 404 if not found.
GET | /stats | Assignment-grade counters | No body | 200: `{ "sent": <int>, "failed": <int>, "queued": <int>, "duplicates_blocked": <int> }`.
GET | /health | Basic health probe | No body | 200: `{ "status": "ok", "service": "linkplease-automation" }`.

Notes:
- POST /webhook verifies HMAC-SHA256 signature using `PSEUDOGRAM_API_KEY` and the raw request body (see `app.security.webhook`). If the signature validation fails, the request is rejected with 401.
- POST /webhook persists the event (unique `event_id`) and returns quickly. Further processing (rule matching and job creation) runs asynchronously via a background task or worker.

---

## 6. Reliability engineering (implementation details)

This section explains how the implementation meets the reliability requirements in the assignment.

### Duplicate events
- The `events` table has a UNIQUE constraint on `event_id`. `webhook_service.persist_event` tries to insert the event and treats IntegrityError for duplicate event_id as a duplicate — these duplicates are acknowledged but not re-processed.
- The webhook endpoint returns `status: duplicate` for repeated deliveries.

### Duplicate DMs (same user & rule)
- DMJobs have a database-level UNIQUE constraint on `(rule_id, recipient_user_id)` which prevents creating more than one DMJob for the same rule/recipient pair.
- When a duplicate insert is attempted, the code catches IntegrityError and writes a `DMJobDuplicateBlock` record so duplicates are counted and visible.

### Idempotency
- Outbound POST /v1/dm/send uses a stable idempotency key: `linkplease-dm-job-{job_id}` (see `dm_worker.build_idempotency_key`). Retries for the same job reuse the same key to help PseudoGram deduplicate on their side.

### Retries
- The DM worker increments `attempts` and uses exponential backoff (configured by `DM_WORKER_RETRY_BASE_SECONDS`) until `DM_WORKER_MAX_ATTEMPTS` is reached. On permanent client errors (400) the job is marked FAILED. On transient errors or 5xx responses the job is scheduled for retry.

### Rate limiting
- A rolling window limit is enforced in `_reserve_send_slot` using the `dm_send_attempts` table and a `DMRateLimitLock` record obtained with `SELECT ... FOR UPDATE`. This serializes access and ensures at most 10 outbound attempts are recorded in a 60-second window.

### Delivery reconciliation
- HTTP 202 is treated as acceptance, not delivery. When a 202 response contains a `dm_id`, the DMJob is marked ACCEPTED and a `Delivery` record is created with status `queued`.
- The ReconciliationWorker polls PseudoGram `GET /v1/dm/{dm_id}` and updates Delivery and DMJob status to `DELIVERED` or `FAILED` depending on the upstream status. If a delivery fails, the DMJob is reset to `RETRYING` with backoff and the `dm_id` cleared so it can be re-sent.

### Persistence
- Important entities persisted: `Event`, `Rule`, `DMJob`, `DMSendAttempt`, `Delivery`, `DMJobDuplicateBlock`.
- Persistence ensures work survives process restarts and that stats reflect durable state.

### Out-of-order events
- Events are processed in order of `received_at` when scanning unprocessed events. However, because webhooks can arrive out-of-order, the system relies on deduplication and idempotent semantics rather than strict chronological guarantees.

### comment.deleted
- `comment.deleted` events are persisted and then no-op processed (the code marks the event processed but does not create DM jobs). This is an explicit design choice documented in the code.

---

## 7. Background workers

The project includes two primary background responsibilities.

- DM worker (`app.services.dm_worker.DMWorker`)
  - Claims at most one DMJob at a time (transactional lease via `claimed_at` and `status` transitions).
  - Reserves a send slot under the rolling rate limit and writes a `DMSendAttempt` before performing the outbound POST.
  - Calls PseudoGram POST /v1/dm/send with an `Idempotency-Key` derived from the DMJob ID.
  - Handles responses: 202 → ACCEPTED, 429 → schedule retry, 4xx → permanent failure, 5xx → retry.
  - Creates or updates a `Delivery` record when an accepted DM returns `dm_id`.

- Reconciliation worker (`app.services.reconciliation.ReconciliationWorker`)
  - Polls `Delivery` rows in QUEUED state and calls PseudoGram GET /v1/dm/{dm_id}.
  - Transitions Delivery/DMJob to DELIVERED or FAILED depending on upstream status.
  - If upstream reports failed, clears `dm_id` and moves DMJob back to RETRYING with a backoff.

Worker placement
- By default the workers are started inside the FastAPI process on startup (in `app.main._start_background_workers`) as daemon threads. This behavior can be disabled using the `DISABLE_BACKGROUND_WORKERS` environment variable. The code also supports running the workers as standalone processes using the `start_worker()` helpers.

---

## 8. Database (models & important tables)

- Database technology: SQLAlchemy ORM (Postgres in production via `render.yaml`; SQLite fallback supported locally via `DATABASE_URL`).

Important entities:
- `rules` (Rule): `id`, `keyword`, `dm_message`, `active`.
- `events` (Event): persistent webhook events: `event_id`, `event_type`, `comment_id`, `user_id`, `text`, `processed`.
- `dm_jobs` (DMJob): persistent DM jobs with `status`, `attempts`, `dm_id`, and uniqueness on `(rule_id, recipient_user_id)`.
- `dm_send_attempts` (DMSendAttempt): timestamped records of outbound attempts used for rolling rate-limit enforcement.
- `deliveries` (Delivery): maps accepted outbound `dm_id` to `dm_job_id` and tracks reconciliation status (queued/delivered/failed).
- `dm_job_duplicate_blocks` (DMJobDuplicateBlock): durable counter/record when a duplicate DMJob insertion was prevented by database uniqueness.

Why persistence matters: durable records enable the system to resume work after restarts, to compute accurate statistics, and to provide strong guarantees against duplicates when combined with database constraints and idempotency keys.

---

## 9. Frontend

The frontend (in `frontend/`) is a React + Vite single-page app that integrates with the backend API:
- Dashboard: live statistics (uses `GET /stats`).
- Automation Rules: create and list rules (`POST /rules`, `GET /rules`).
- System Status: checks `GET /health` and displays a polished status overview.

The UI is a dark SaaS-styled interface branded as **LinkPlease**. The frontend uses environment variable `VITE_API_BASE_URL` to point to the backend API during development.

---

## 10. Tech stack

Component | Technology
---|---
Frontend | React + Vite
Backend | FastAPI (Python)
ORM / DB | SQLAlchemy (Postgres recommended in deploy, SQLite supported locally)
HTTP client | httpx
Mock upstream API | PseudoGram (`https://pseudogram-api.onrender.com`)
Testing | pytest (backend tests)
Deployment | Render-compatible `render.yaml` provided (web + managed Postgres)

---

## 11. Project structure (top-level)

```
LinkPLEASE/
├── backend/
│   ├── app/                  # FastAPI application: api, models, services, schemas
│   ├── alembic/              # DB migrations
│   └── tests/                # Backend tests (pytest)
├── frontend/                 # React + Vite frontend
├── FAILURES.md               # Known failure modes and tradeoffs
├── render.yaml               # Render deployment configuration (example)
└── README.md                 # (this file)
```

Ignored/generated directories (not shown): `node_modules`, `frontend/dist`, Python venvs, `.pytest_cache`, etc.

---

## 12. Local setup & development

_Prerequisites:_ Docker (for the Docker development workflow below) or Python 3.10+ and Node.js if you prefer the traditional local setup. See the Docker Development section after the local setup steps.



Prerequisites: Python 3.10+ (tested), Node.js 16+/npm, and a local database if you want Postgres behavior. SQLite works for local testing.

Backend (local):

```bash
# from repository root
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# or: source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
# ensure DATABASE_URL is set (SQLite example):
export DATABASE_URL="sqlite:///./linkplease.db"    # POSIX
set DATABASE_URL=sqlite:///./linkplease.db          # Windows PowerShell
# Run migrations (if using alembic locally):
alembic upgrade head
# Start the API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

To run workers separately (optional):

```bash
cd backend
# DM worker
python -m app.services.dm_worker
# Reconciliation worker
python -m app.services.reconciliation
```

Frontend (local):

```bash
cd frontend
npm install --no-audit --no-fund
# Set VITE_API_BASE_URL to backend (default is http://127.0.0.1:8000)
npm run dev
# Production build
npm run build
```

Environment variable used by frontend: `VITE_API_BASE_URL` — base URL of backend API (e.g. `http://127.0.0.1:8000`). See `frontend/.env.example`.

---

## Docker Development

A Docker-based development environment is provided to make local setup reproducible without requiring Python or other runtime tooling on the host. It uses Docker Compose to provide a backend service and a PostgreSQL database.

Note: the repository already supports SQLite for simple local runs. Docker Compose is recommended for a reproducible Postgres-backed development environment.

Quick start (after installing Docker and Docker Compose):

1. Copy environment variables into a local `.env` (or set them in your shell). The repository provides `backend/.env.example` as a reference. Do NOT commit `.env`.

2. Build and start services:

```bash
# from repository root
docker compose up --build
```

3. Verify the backend is running and healthy:

- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

4. Run backend tests inside the container (optional):

```bash
# run tests in the running backend container
docker compose exec backend pytest -q
```

5. Run Alembic migrations (if using Postgres locally):

```bash
# upgrade DB to latest revision
docker compose exec backend alembic upgrade head
```

Environment variables used by Compose (set in host `.env` or export before starting):
- PSEUDOGRAM_API_KEY  (required to call PseudoGram; do NOT commit)
- FRONTEND_URL        (optional)
- Any variables listed in `backend/.env.example` (DATABASE_URL is set by Compose)

The Docker image for the backend is built from `backend/Dockerfile` and runs the same FastAPI app and in-process workers as the non-Dockerized setup. The container respects `PORT` (default 8000) so it is suitable for Render deployments that use Docker images.

---

## 13. Environment variables (names only)

- `DATABASE_URL` — SQLAlchemy database URL (Postgres recommended in production).
- `PSEUDOGRAM_BASE_URL` — Base URL for the mock PseudoGram API (default in `render.yaml` is `https://pseudogram-api.onrender.com`).
- `PSEUDOGRAM_API_KEY` — API key used to call and verify PseudoGram endpoints and webhook signatures.
- `DM_WORKER_MAX_ATTEMPTS` — Maximum retry attempts for DM worker.
- `DM_WORKER_RETRY_BASE_SECONDS` — Base seconds used for exponential backoff.
- `DM_WORKER_SENDING_LEASE_SECONDS` — Lease duration to consider a claimed DMJob stale.
- `FRONTEND_URL` — Optional frontend origin added to CORS allowed origins.
- `DISABLE_BACKGROUND_WORKERS` — If set to `1`/`true`, the web process will not start background worker threads.

Do not store real secrets in the repository. Use environment configuration or platform secret management.

---

## 14. Testing

Backend unit tests (pytest):

```bash
cd backend
pytest -q
```

- Verified locally during this session: **62 tests passed** (see `backend/tests`).

Frontend build:

```bash
cd frontend
npm install --no-audit --no-fund
npm run build
```

- Verified locally during this session: frontend build completed successfully.

---

## 15. Assignment coverage (requirements)

| Requirement | Implementation | Status |
|---|---|:---:|
| PART A.1 Create a rule → DM commenter when keyword appears | `POST /rules` creates rules; `event_processor` matches active rules and creates `DMJob` rows | Implemented ✅ |
| PART A.2 Incoming comments matched against rules | `event_processor.matching_rules` performs case-insensitive substring matches | Implemented ✅ |
| PART A.3 Same user must not receive same rule DM twice | DB UNIQUE constraint on `(rule_id, recipient_user_id)` prevents duplicated DMJobs; duplicates recorded in `dm_job_duplicate_blocks` | Implemented ✅ |
| PART A.4 No DM silently lost when mock API fails | Retries, persistent DMSendAttempt, and Delivery reconciliation reduce silent loss; see FAILURES.md for known edge cases | Implemented (with documented limitations) ✅ |
| PART B.1 Verify webhook signatures | Signature verification implemented (`app.security.webhook`) using HMAC-SHA256 against `PSEUDOGRAM_API_KEY` | Implemented ✅ |
| PART B.2 `GET /stats` live numbers | `GET /stats` returns exact counters derived from DB state | Implemented ✅ |
| PART C.1 Reconcile delivery status (202 is accepted) | Reconciliation worker polls PseudoGram `GET /v1/dm/{dm_id}` and updates Delivery/DMJob | Implemented ✅ |
| PART C.2 Handle `comment.deleted` | `comment.deleted` events are persisted and processed as a no-op (event marked processed) | Implemented (no-op) ✅ |
| PART C.3 Handle 500 comments in 10s without losing events or violating rate limit | Durable DB persistence and rate-limit enforcement are implemented; stress verification is documented but full 500-event evaluator test is expected to run against a deployed instance | Implemented (designed for) ✅ /

Notes:
- The repository contains known failure modes (see `FAILURES.md`). Some edge cases (for example, process crash between marking accepted and creating Delivery record) are documented and suggestions for hardening are included there.
- The official grader may send 500 events; the system is designed to persist events and enforce rate limits, but grader verification should be performed against a deployed instance.

---

## 16. Deployment

- GitHub repository: `https://github.com/HarshithhKumar/LinkPLEASE`
- `render.yaml` included for Render deployments (starts web service and configures a managed Postgres DB). The file documents `PSEUDOGRAM_BASE_URL` and that workers run inside the web process.

Live URL:

`<DEPLOYMENT_URL_TO_BE_ADDED>`

(Do not replace the placeholder with an invented URL.)

Backend start command (used in `render.yaml`):

```
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment variables required for deployment are listed in section **13** above.

---

## 17. Reliability / load testing notes

Local verification included:
- Single-DM end-to-end worker tests (local worker + backend) — exercised during development.
- 10-DM end-to-end worker test run locally during development (see tests and local scripts).

The official 500-event assignment verification should be executed against a deployed service. The grader will compare `/stats` results against server-side truth.

---

## 18. Known limitations

See `FAILURES.md` for a precise list of known failure modes and recommended mitigations. The project intentionally documents these limitations rather than hiding them.

---

## 19. Security

- API keys and secrets must be set as environment variables (never checked into the repo). The frontend does not contain PseudoGram credentials.
- Webhook signatures are verified using HMAC-SHA256 (`X-PseudoGram-Signature: sha256=<hex>`).
- CORS allows local development origins and the optional `FRONTEND_URL` if configured.

---

## 20. Engineering decisions / trade-offs

- Durable DB-backed job state (DMJob, Delivery, DMSendAttempt) provides strong recovery semantics at the cost of more writes and slightly higher latency.
- Workers run inside the FastAPI process by default for simplicity on single-instance hosting (Render free tier). This is configurable by `DISABLE_BACKGROUND_WORKERS` and workers can be run as separate processes.
- Idempotency keys are derived from DMJob IDs to minimize duplicate sends when retries occur.
- Reconciliation is used because HTTP 202 only indicates acceptance, not final delivery.

---

## 21. Submission checklist

- [x] Public GitHub repository
- [x] README.md (this file)
- [x] FAILURES.md preserved
- [ ] Working deployed URL (`<DEPLOYMENT_URL_TO_BE_ADDED>`)
- [x] Environment secrets configured outside Git
- [x] Backend tests passing locally (verified: 62 passed)
- [x] Frontend build passing locally (verified)
- [ ] Assignment submission completed (ensure deployment URL is provided)

---

## 22. Closing statement

LinkPlease is an internship-level implementation that demonstrates durable, idempotent handling of Instagram-style comment webhooks and automated DM delivery. The project focuses on correctness under duplicates, transient failures, rate limits, and delayed delivery, and documents known failure modes and improvements in `FAILURES.md`.

For a reviewer: start the backend, create a rule via `POST /rules`, POST signed `comment.created` events to `/webhook`, and observe `GET /stats` and the frontend dashboard to verify behavior.

---

If you want, I can now write this README.md into the repository (local file only), show the full file contents, and run `git diff -- README.md` so you can review the exact changes (I will not commit or push unless instructed).