from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class WeeklyReport(Base, TimestampMixin):
    __tablename__ = "weekly_reports"
    __table_args__ = (UniqueConstraint("member_id", "week_start", name="uq_member_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("member_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)

    work_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    experiment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    problems: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_week_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    need_help: Mapped[str | None] = mapped_column(Text, nullable=True)

    self_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True, nullable=False)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
