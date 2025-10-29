from __future__ import annotations
from contextlib import contextmanager
from typing import Any, Dict, Generator, Iterable, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings

# -----------------------------------------------------------------------------
# 1) Engine + Session (pool de conexões)
# -----------------------------------------------------------------------------

_engine = Optional[Engine] = None
_SessionLocal = Optional[sessionmaker] = None

def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            future=True,
        )
        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _engine

@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_session() -> Generator[Session, None, None]:
    if _SessionLocal in None:
        get_engine()
    assert _SessionLocal is not None
    db:Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
# -----------------------------------------------------------------------------
# 2) Healthcheck (pronto para /healthz e /readyz)
# -----------------------------------------------------------------------------

def health_check() -> bool:
    eng = get_engine()
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))

        db = conn.execute(text("SELECT current_database()")).scalar()
        user = conn.execute(text("SELECT current_user")).scalar_one()
        version = conn.execute(text("SELECT version()")).scalar_one()
        return {
            "ok": True,
            "database": db,
            "user": user,
            "version": version,
        }

# -----------------------------------------------------------------------------
# 3) Helpers de consulta (SELECT) e execução (DML/DDL)
# -----------------------------------------------------------------------------

def fetch_all(sql:str, params:Optional[Dict[str,Any]] = None, 
              timeout_ms: Optional[int] = None) -> List[Dict[str, Any]]:
    eng = get_engine()
    with eng.connect() as conn:
        if timeout_ms:
            conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result: Result = conn.execute(text(sql), params or {})
        rows = result.mappings().all()
        return [dict(r) for r in rows]

def fetch_one(sql:str, params:Optional[Dict[str, Any]] = None,
              timeout_ms: Optional[int] = None) -> Optional[Dict[str, Any]]:
    rows = fetch_all(sql, params=params, timeout_ms=timeout_ms)
    return rows[0] if rows else None

def execute(sql:str, params: Optional[Dict[str, Any]] = None) -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text(sql), params or {})

# -----------------------------------------------------------------------------
# 4) Refresh de Materialized Views (MV)
# -----------------------------------------------------------------------------

def refresh_materialized_views(name: str, *, concurrently: bool = True) -> None:
    eng = get_engine()
    sql = (f"REFRESH MATERIALIZED VIEW CONCURRENTLY {name}" if concurrently else f"REFRESH MATERIALIZED VIEW {name}")

    if concurrently:
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(sql))
    else:
        with eng.begin() as conn:
            conn.execute(text(sql))

# -----------------------------------------------------------------------------
# 5) (Opcional) Utilitário para janelas de tempo (granularidade)
# -----------------------------------------------------------------------------

def date_trunc_expr(grain: str,  column: str = "created_at") -> str:
    allowed = {"hour", "day", "week", "month"}
    if grain not in allowed:
        raise ValueError(f"Granularidade invalida: {grain}")
    return f"date_trunc('{grain}', {column})"