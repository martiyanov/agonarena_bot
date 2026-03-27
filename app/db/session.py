from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import get_database_url_for_env

engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker | None = None


def configure_database(database_url: str | None = None) -> None:
    global engine, AsyncSessionLocal
    engine = create_async_engine(database_url or get_database_url_for_env(), future=True, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


configure_database()
