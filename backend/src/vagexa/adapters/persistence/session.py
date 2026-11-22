from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vagexa.config import Settings

_engine = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(settings: Settings) -> None:
    global _engine, _session_factory
    _engine = create_engine(settings.database_url, pool_pre_ping=True)
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def session_scope() -> Iterator[Session]:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialised")
    db = _session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def open_session() -> Session:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialised")
    return _session_factory()


def check_database() -> None:
    if _engine is None:
        raise RuntimeError("Database engine is not initialised")
    with _engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
