from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DuelMessage(Base):
    """Одна реплика в поединке.

    MVP-вариант: без сложной структуры, просто текст + указание автора и раунда.
    """

    __tablename__ = "duel_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    duel_id: Mapped[int] = mapped_column(ForeignKey("duels.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, index=True)
    author: Mapped[str] = mapped_column(String(16), index=True)  # "user" | "ai"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
