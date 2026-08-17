from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread, Event
import threading
import time
import os

from app.api.rules import router as rules_router
from app.api.webhook import router as webhook_router
from app.api.stats import router as stats_router
from app.config import get_settings

# Import worker classes lazily to avoid import-time side effects
from app.services.dm_worker import DMWorker
from app.services.reconciliation import ReconciliationWorker

app = FastAPI(
    title="LinkPlease Automation API",
    description="Instagram comment-to-DM automation service",
    version="1.0.0",
)

app.include_router(rules_router)
app.include_router(webhook_router)
app.include_router(stats_router)

# Configure CORS: allow local dev origins and optional FRONTEND_URL from env
settings = get_settings()
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if getattr(settings, "frontend_url", None):
    if settings.frontend_url.strip():
        allowed_origins.append(settings.frontend_url.strip())

# Remove duplicates while preserving order
_seen = set()
_allowed = []
for o in allowed_origins:
    if o not in _seen and o:
        _seen.add(o)
        _allowed.append(o)
_allowed_origins = _allowed

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "linkplease-automation",
    }


# Background worker management for Render Free (run workers inside web process)
def _dm_worker_loop(stop_event: Event):
    worker = DMWorker()
    while not stop_event.is_set():
        try:
            result = worker.run_worker_once()
            # If nothing claimed or rate-limited, sleep a bit to avoid busy-looping
            if not result.claimed or result.rate_limited:
                # wait with timeout so we can respond promptly to shutdown
                stop_event.wait(1.0)
            else:
                # continue immediately to drain work
                continue
        except Exception:
            # Log and back off on unexpected errors
            try:
                import logging
                logging.exception('Unexpected error in DM worker loop')
            except Exception:
                pass
            stop_event.wait(1.0)


def _reconciliation_loop(stop_event: Event):
    worker = ReconciliationWorker()
    while not stop_event.is_set():
        try:
            result = worker.run_once()
            if result.processed == 0:
                stop_event.wait(5.0)
            else:
                continue
        except Exception:
            try:
                import logging
                logging.exception('Unexpected error in reconciliation loop')
            except Exception:
                pass
            stop_event.wait(5.0)


@app.on_event('startup')
def _start_background_workers():
    # Avoid starting multiple times in case startup is called more than once
    if getattr(app.state, 'workers_started', False):
        return

    # Do not start workers if explicitly disabled
    if os.getenv('DISABLE_BACKGROUND_WORKERS', '').lower() in ('1','true','yes'):
        app.state.workers_started = False
        return

    stop_event = Event()
    app.state.worker_stop_event = stop_event

    dm_thread = Thread(target=_dm_worker_loop, args=(stop_event,), name='dm-worker-thread', daemon=True)
    recon_thread = Thread(target=_reconciliation_loop, args=(stop_event,), name='recon-worker-thread', daemon=True)

    dm_thread.start()
    recon_thread.start()

    app.state.dm_thread = dm_thread
    app.state.recon_thread = recon_thread
    app.state.workers_started = True


@app.on_event('shutdown')
def _stop_background_workers():
    stop_event = getattr(app.state, 'worker_stop_event', None)
    if stop_event is None:
        return
    try:
        stop_event.set()
        # Join threads with timeout to avoid blocking shutdown indefinitely
        dm = getattr(app.state, 'dm_thread', None)
        rc = getattr(app.state, 'recon_thread', None)
        if dm is not None:
            dm.join(timeout=2.0)
        if rc is not None:
            rc.join(timeout=2.0)
    except Exception:
        pass
