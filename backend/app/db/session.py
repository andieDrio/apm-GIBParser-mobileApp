from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _prepare_sqlite_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        raw = url.removeprefix("sqlite:///")
        Path(raw).parent.mkdir(parents=True, exist_ok=True)
    return url


engine = create_engine(
    _prepare_sqlite_url(settings.database_url),
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
