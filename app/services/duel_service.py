from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Duel, DuelRound, Scenario


class DuelService:
    async def get_scenario_by_code(self, session: AsyncSession, code: str) -> Scenario | None:
        result = await session.execute(select(Scenario).where(Scenario.code == code, Scenario.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def create_duel(self, session: AsyncSession, telegram_user_id: int, scenario: Scenario) -> Duel:
        duel = Duel(
            status="ready",
            scenario_id=scenario.id,
            user_telegram_id=telegram_user_id,
            current_round_number=1,
            turn_time_limit_sec=90,
            user_role_round1=scenario.role_a_name,
            ai_role_round1=scenario.role_b_name,
            user_role_round2=scenario.role_b_name,
            ai_role_round2=scenario.role_a_name,
        )
        session.add(duel)
        await session.flush()

        round_1 = DuelRound(
            duel_id=duel.id,
            round_number=1,
            status="pending",
            user_role=scenario.role_a_name,
            ai_role=scenario.role_b_name,
            opening_line=scenario.opening_line_b,
        )
        round_2 = DuelRound(
            duel_id=duel.id,
            round_number=2,
            status="pending",
            user_role=scenario.role_b_name,
            ai_role=scenario.role_a_name,
            opening_line=scenario.opening_line_a,
        )
        session.add_all([round_1, round_2])
        await session.commit()
        await session.refresh(duel)
        return duel

    async def get_duel_rounds(self, session: AsyncSession, duel_id: int) -> list[DuelRound]:
        result = await session.execute(
            select(DuelRound).where(DuelRound.duel_id == duel_id).order_by(DuelRound.round_number.asc())
        )
        return list(result.scalars().all())
