from fastapi import FastAPI
from app.core.config import settings
from app.db.init_db import init_db

app = FastAPI(title=settings.app_name, version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get(f"{settings.api_prefix}/status")
def status() -> dict[str, object]:
    settings.validate_runtime()
    return {
        "status": "OPERATIONAL",
        "groupib": {"configured": bool(settings.group_ib_username and settings.group_ib_api_token)},
    }
