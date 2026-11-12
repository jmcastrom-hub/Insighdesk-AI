import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    default_path = Path(__file__).resolve().parents[1] / "insightdesk.db"
    url = database_url or os.getenv("DATABASE_URL", f"sqlite:///{default_path.as_posix()}")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    database_engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):
        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database_engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db


def migrate_sqlite_schema(database_engine=engine) -> None:
    """Add nullable/defaulted fields to existing local SQLite databases."""
    if database_engine.dialect.name != "sqlite":
        return
    additions = {
        "productos": {
            "existencias": "INTEGER NOT NULL DEFAULT 0",
        },
        "ventas": {
            "vendedor_id": "INTEGER NULL REFERENCES vendedores(id)",
            "moneda_pago": "VARCHAR(3) NOT NULL DEFAULT 'CRC'",
            "monto_moneda": "NUMERIC(14, 4) NULL",
            "tipo_cambio": "NUMERIC(14, 6) NOT NULL DEFAULT 1",
            "fecha_tipo_cambio": "DATE NULL",
            "estado_pago": "VARCHAR(20) NOT NULL DEFAULT 'confirmada'",
        },
    }
    inspector = inspect(database_engine)
    with database_engine.begin() as connection:
        for table, columns in additions.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'))
