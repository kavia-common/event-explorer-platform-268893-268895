from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _get_database_url() -> str:
    """
    Resolve database URL from environment.

    We intentionally do not hard-code connection details.
    Expected env var: DATABASE_URL (or POSTGRES_URL as a fallback).
    """
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not database_url:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL (preferred) or POSTGRES_URL in the environment."
        )
    return database_url


_ENGINE: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get (or create) the SQLAlchemy engine."""
    global _ENGINE, _SessionLocal
    if _ENGINE is None:
        _ENGINE = create_engine(_get_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_ENGINE)
    return _ENGINE


def get_sessionmaker() -> sessionmaker[Session]:
    """Get (or create) the SessionLocal factory."""
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager that yields a DB session and ensures proper commit/rollback."""
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
