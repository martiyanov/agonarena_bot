from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JudgeResult(Base):
    __tablename__ = "judge_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    duel_id: Mapped[int] = mapped_column(ForeignKey("duels.id"), index=True)
    judge_type: Mapped[str] = mapped_column(String(64), index=True)
    winner: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str] = mapped_column(Text)
    round1_comment: Mapped[str] = mapped_column(Text, nullable=True)
    round2_comment: Mapped[str] = mapped_column(Text, nullable=True)
