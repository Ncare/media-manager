"""SQLite engine + session helpers (WAL mode for concurrent read)."""
import sqlite3
import logging

from sqlalchemy import event, inspect
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

log = logging.getLogger("media_manager.db")

# check_same_thread=False: FastAPI may use threads; SQLModel handles pooling.
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):  # pragma: no cover
    """Enable WAL + sane synchronous level for NAS (single-writer, many readers)."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def _migrate_columns() -> None:
    """Idempotently ADD COLUMN for any model field missing in an existing DB.

    SQLModel.metadata.create_all only creates missing tables, not missing
    columns. For a lightweight NAS app without Alembic, we derive each model's
    nullable columns and ALTER TABLE when absent. New NOT NULL columns are
    intentionally avoided to keep migrations safe.
    """
    # Map tablename -> {column_name: sql_type_guess}
    targets: dict[str, dict[str, str]] = {}
    for table_name, table in SQLModel.metadata.tables.items():
        cols: dict[str, str] = {}
        for col in table.columns:
            if col.primary_key:
                continue
            try:
                sqltype = col.type.dialect_impl(sqlite3.dialect()).compile()
            except Exception:
                sqltype = str(col.type)
            # Everything we add is nullable; coerce NOT NULL types to nullable.
            sqltype = sqltype.replace("NOT NULL", "").strip()
            cols[col.name] = sqltype or "TEXT"
        targets[table_name] = cols

    db_path = str(settings.db_path)
    if not db_path:
        return
    conn = sqlite3.connect(db_path)
    try:
        existing_tables = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for table_name, cols in targets.items():
            if table_name not in existing_tables:
                continue
            present = {r[1] for r in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()}
            for col_name, sqltype in cols.items():
                if col_name not in present:
                    log.info("migrate: ADD COLUMN %s.%s (%s)", table_name, col_name, sqltype)
                    conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {sqltype}')
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables. Importing model modules registers them on SQLModel.metadata."""
    import importlib
    import pkgutil

    import app.models as models_pkg
    for mod in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"app.models.{mod.name}")

    SQLModel.metadata.create_all(engine)
    _migrate_columns()


def get_session():
    with Session(engine) as session:
        yield session
