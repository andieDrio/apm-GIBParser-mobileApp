from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.reports import router as reports_router
from app.api.runs import router as runs_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.repository import reconcile_nonterminal_runs
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        reconcile_nonterminal_runs(db)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(runs_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/status")
def status() -> dict[str, object]:
    settings.validate_runtime()
    return {
        "status": "OPERATIONAL",
        "groupib": {"configured": bool(settings.group_ib_username and settings.group_ib_api_token)},
    }
