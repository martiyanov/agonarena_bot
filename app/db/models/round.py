from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DuelRound(Base):
    __tablename__ = "duel_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    duel_id: Mapped[int] = mapped_column(ForeignKey("duels.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")

    user_role: Mapped[str] = mapped_column(String(128))
    ai_role: Mapped[str] = mapped_column(String(128))
    opening_line: Mapped[str] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
