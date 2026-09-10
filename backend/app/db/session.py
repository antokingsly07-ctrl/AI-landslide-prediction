"""SQLAlchemy database setup with PostgreSQL/PostGIS support and SQLite fallback."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}


def _normalise_database_url(url: str) -> str:
    """Route postgres URLs to psycopg3 (installed), not the psycopg2 default."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


engine = create_engine(
    _normalise_database_url(settings.DATABASE_URL),
    connect_args=connect_args,
    pool_pre_ping=True,
)


if settings.is_sqlite:
    # Enable foreign keys for SQLite development fallback
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. In production use Alembic migrations; this is a dev helper."""
    from app import models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)
