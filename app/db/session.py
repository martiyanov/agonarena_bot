from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_database_url_for_env

engine = create_async_engine(get_database_url_for_env(), future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
