import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scenario


class ScenarioService:
    def __init__(self, seed_path: str = "seeds/scenarios.json"):
        self.seed_path = Path(seed_path)

    async def seed_if_empty(self, session: AsyncSession) -> int:
        payload = json.loads(self.seed_path.read_text(encoding="utf-8"))

        existing_codes_result = await session.execute(select(Scenario.code))
        existing_codes = set(existing_codes_result.scalars().all())

        scenarios = [Scenario(**item) for item in payload if item["code"] not in existing_codes]
        if not scenarios:
            return 0

        session.add_all(scenarios)
        await session.commit()
        return len(scenarios)

    async def list_active(self, session: AsyncSession) -> list[Scenario]:
        result = await session.execute(select(Scenario).where(Scenario.is_active.is_(True)).order_by(Scenario.id.asc()))
        return list(result.scalars().all())
