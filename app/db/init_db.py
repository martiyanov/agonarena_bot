from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.db import models  # noqa: F401
from app.services.scenario_service import ScenarioService


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await ScenarioService().seed_if_empty(session)
