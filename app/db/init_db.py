from app.db.base import Base
from app.db import models  # noqa: F401
from app.db import session as db_session
from app.services.scenario_service import ScenarioService


async def init_db() -> None:
    async with db_session.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db_session.AsyncSessionLocal() as session:
        await ScenarioService().seed_if_empty(session)
