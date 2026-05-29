from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_version_metadata_columns()


def _ensure_version_metadata_columns() -> None:
    inspector = inspect(engine)
    migrations = {
        "sysml_models": [
            ("branch_name", "VARCHAR(80) NOT NULL DEFAULT 'main'"),
            ("version_tag", "VARCHAR(80) NULL"),
        ],
        "document_templates": [
            ("branch_name", "VARCHAR(80) NOT NULL DEFAULT 'main'"),
            ("version_tag", "VARCHAR(80) NULL"),
        ],
        "document_template_versions": [
            ("branch_name", "VARCHAR(80) NOT NULL DEFAULT 'main'"),
            ("version_tag", "VARCHAR(80) NULL"),
        ],
    }
    with engine.begin() as conn:
        for table_name, columns in migrations.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns:
                if column_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
