from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Duel(Base):
    __tablename__ = "duels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    user_telegram_id: Mapped[int] = mapped_column(index=True)

    current_round_number: Mapped[int] = mapped_column(Integer, default=1)
    turn_time_limit_sec: Mapped[int] = mapped_column(Integer, default=90)

    user_role_round1: Mapped[str] = mapped_column(String(128))
    ai_role_round1: Mapped[str] = mapped_column(String(128))
    user_role_round2: Mapped[str] = mapped_column(String(128))
    ai_role_round2: Mapped[str] = mapped_column(String(128))

    final_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
