from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="general")
    difficulty: Mapped[str] = mapped_column(String(32), default="normal")

    role_a_name: Mapped[str] = mapped_column(String(128))
    role_a_goal: Mapped[str] = mapped_column(Text)
    role_b_name: Mapped[str] = mapped_column(String(128))
    role_b_goal: Mapped[str] = mapped_column(Text)

    opening_line_a: Mapped[str] = mapped_column(Text)
    opening_line_b: Mapped[str] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
