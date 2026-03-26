import math
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Duel, DuelMessage, DuelRound, JudgeResult, Scenario


class DuelService:
    async def get_scenario_by_code(self, session: AsyncSession, code: str) -> Scenario | None:
        result = await session.execute(select(Scenario).where(Scenario.code == code, Scenario.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def get_scenario_by_id(self, session: AsyncSession, scenario_id: int) -> Scenario | None:
        result = await session.execute(select(Scenario).where(Scenario.id == scenario_id))
        return result.scalar_one_or_none()

    async def create_duel(self, session: AsyncSession, telegram_user_id: int, scenario: Scenario) -> Duel:
        now = datetime.utcnow()
        duel = Duel(
            status="in_progress",
            scenario_id=scenario.id,
            user_telegram_id=telegram_user_id,
            current_round_number=1,
            turn_time_limit_sec=120,
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
            started_at=None,
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

    async def get_duel(self, session: AsyncSession, duel_id: int) -> Duel | None:
        result = await session.execute(select(Duel).where(Duel.id == duel_id))
        return result.scalar_one_or_none()

    async def get_duel_rounds(self, session: AsyncSession, duel_id: int) -> list[DuelRound]:
        result = await session.execute(
            select(DuelRound).where(DuelRound.duel_id == duel_id).order_by(DuelRound.round_number.asc())
        )
        return list(result.scalars().all())

    async def get_latest_duel_for_user(self, session: AsyncSession, telegram_user_id: int) -> Duel | None:
        result = await session.execute(
            select(Duel).where(Duel.user_telegram_id == telegram_user_id).order_by(desc(Duel.id)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_round(self, session: AsyncSession, duel_id: int, round_number: int) -> DuelRound | None:
        result = await session.execute(
            select(DuelRound).where(
                DuelRound.duel_id == duel_id,
                DuelRound.round_number == round_number,
            )
        )
        return result.scalar_one_or_none()

    async def ensure_round_started(self, duel: Duel, round_obj: DuelRound) -> None:
        if duel.status == "ready":
            duel.status = "in_progress"
        if round_obj.status == "pending":
            round_obj.status = "in_progress"
            round_obj.started_at = datetime.utcnow()

    def get_round_deadline(self, duel: Duel, round_obj: DuelRound) -> datetime | None:
        if round_obj.started_at is None:
            return None
        return round_obj.started_at + timedelta(seconds=duel.turn_time_limit_sec)

    def get_seconds_left(self, duel: Duel, round_obj: DuelRound) -> int | None:
        deadline = self.get_round_deadline(duel, round_obj)
        if deadline is None:
            return None
        return max(0, math.ceil((deadline - datetime.utcnow()).total_seconds()))

    def is_round_expired(self, duel: Duel, round_obj: DuelRound) -> bool:
        deadline = self.get_round_deadline(duel, round_obj)
        return deadline is not None and datetime.utcnow() >= deadline

    async def list_messages_for_round(self, session: AsyncSession, duel_id: int, round_number: int) -> list[DuelMessage]:
        result = await session.execute(
            select(DuelMessage)
            .where(
                DuelMessage.duel_id == duel_id,
                DuelMessage.round_number == round_number,
            )
            .order_by(DuelMessage.id.asc())
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        session: AsyncSession,
        duel_id: int,
        round_number: int,
        author: str,
        content: str,
    ) -> DuelMessage:
        message = DuelMessage(
            duel_id=duel_id,
            round_number=round_number,
            author=author,
            content=content,
        )
        session.add(message)
        await session.flush()
        return message

    async def complete_round(self, duel: Duel, round_obj: DuelRound) -> None:
        round_obj.status = "finished"
        if round_obj.started_at is None:
            round_obj.started_at = datetime.utcnow()
        round_obj.finished_at = datetime.utcnow()

        if round_obj.round_number == 1:
            duel.current_round_number = 2
            duel.status = "in_progress"
        else:
            duel.status = "judging"

    async def finish_duel(self, duel: Duel, final_verdict: str) -> None:
        duel.status = "finished"
        duel.final_verdict = final_verdict
        duel.updated_at = datetime.utcnow()

    async def list_judge_results(self, session: AsyncSession, duel_id: int) -> list[JudgeResult]:
        result = await session.execute(
            select(JudgeResult).where(JudgeResult.duel_id == duel_id).order_by(JudgeResult.id.asc())
        )
        return list(result.scalars().all())
