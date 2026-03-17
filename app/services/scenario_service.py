import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scenario


class ScenarioService:
    def __init__(self, seed_path: str = "seeds/scenarios.json"):
        self.seed_path = Path(seed_path)

    async def seed_if_empty(self, session: AsyncSession) -> int:
        existing = await session.execute(select(Scenario.id).limit(1))
        if existing.first() is not None:
            return 0

        payload = json.loads(self.seed_path.read_text(encoding="utf-8"))
        scenarios = [Scenario(**item) for item in payload]
        session.add_all(scenarios)
        await session.commit()
        return len(scenarios)

    async def list_active(self, session: AsyncSession) -> list[Scenario]:
        result = await session.execute(select(Scenario).where(Scenario.is_active.is_(True)).order_by(Scenario.id.asc()))
        return list(result.scalars().all())
