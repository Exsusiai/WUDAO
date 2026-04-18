"""Database engine, session dependency, and table initialization."""
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from services.api.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # required for SQLite
    echo=(settings.app_env != "production"),
)


def init_db() -> None:
    """Create all tables defined in SQLModel metadata."""
    # Import all models so their metadata is registered before create_all
    import python.core.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
