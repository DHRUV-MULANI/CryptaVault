"""SQLAlchemy engine, session, and schema bootstrap."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from cryptavault_api.settings import settings

_connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all CryptaVault tables."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    if any(r[1] == column for r in rows):
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    """Create tables and seed local demo data."""
    from cryptavault_api import models  # noqa: F401
    from cryptavault_api.seed import seed_defaults

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _ensure_column(conn, "shares", "recipient_email", "VARCHAR(320)")
        _ensure_column(conn, "shares", "pin_hash", "TEXT")
    with SessionLocal() as db:
        seed_defaults(db)


def database_healthy() -> bool:
    """Return True when the configured database answers a trivial query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
