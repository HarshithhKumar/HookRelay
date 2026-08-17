# LinkPLEASE

LinkPLEASE is an Instagram comment-to-DM automation backend used for the LinkPlease tech assignment.

What it does
- Receives signed webhooks for Instagram comments.
- Matches comment text against active rules (case-insensitive substring match).
- Creates durable DMJob records to send DMs to users via the PseudoGram API.
- Uses a durable worker to accept outbound DMs with PseudoGram respecting a rolling rate limit.
- Reconciles delivery status via PseudoGram GET /v1/dm/{dm_id} and updates durable state.
- Exposes a /stats endpoint with aggregated counters.

Architecture
- FastAPI application for HTTP endpoints.
- SQLAlchemy ORM with Alembic migrations and SQLite fallback (DATABASE_URL env).
- Durable worker processes for sending DMs and for delivery reconciliation.
- Idempotency and duplicate-block enforcement at the database layer.

Tech stack
- Python, FastAPI, SQLAlchemy, Alembic, httpx

Project structure
- backend/app - application source
- backend/alembic - migrations
- backend/tests - unit tests

Core flow
Webhook -> Event -> Rule matching -> DMJob -> Durable worker -> PseudoGram -> Delivery reconciliation -> Stats

API endpoints
- POST /rules
- POST /webhook
- GET /stats
- GET /health

Configuration
Set via environment variables (do NOT store secrets in the repository):
- DATABASE_URL
- PSEUDOGRAM_BASE_URL
- PSEUDOGRAM_API_KEY
- DM_WORKER_MAX_ATTEMPTS
- DM_WORKER_RETRY_BASE_SECONDS
- DM_WORKER_SENDING_LEASE_SECONDS

Local setup
- Create a Python environment and install requirements: pip install -r backend/requirements.txt
- Run migrations: alembic upgrade head
- Run tests: cd backend && pytest -q
- Start app: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
- Start worker(s): python -m app.services.dm_worker (or run start_worker in a managed process)

Testing
- Tests live in backend/tests. They use a test SQLite database and fixtures.

Rate-limit strategy
- Durable DMSendAttempt records maintain a rolling window limit (10 requests per 60 seconds).
- A DMRateLimitLock row is used with FOR UPDATE to serialize access across workers.

Idempotency strategy
- Outbound idempotency key is stable per DMJob: linkplease-dm-job-{job_id}
- Retries reuse the same idempotency key to avoid duplicate sends for the same logical job.

Retry strategy
- Exponential backoff using DM_WORKER_RETRY_BASE_SECONDS as base.

Delivery reconciliation
- Accepted outbound DMs create a Delivery record and are polled with GET /v1/dm/{dm_id} until delivered or failed.

Stats semantics
- GET /stats returns counts of sent (delivered), failed (permanently failed DMJobs), queued (non-terminal DMJobs), and duplicates_blocked (durable duplicate records).

Known limitations
See FAILURES.md for concrete failure modes and suggestions for improvement.

