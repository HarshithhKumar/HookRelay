from fastapi import FastAPI

from app.api.rules import router as rules_router
from app.api.webhook import router as webhook_router

app = FastAPI(
    title="LinkPlease Automation API",
    description="Instagram comment-to-DM automation service",
    version="1.0.0",
)

app.include_router(rules_router)
app.include_router(webhook_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "linkplease-automation",
    }
