from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import MemberProfile, User


class WeeklyReport(Base, TimestampMixin):
    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("member_id", "week_start", name="uq_member_week"),
    )

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
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # legacy columns from the removed review workflow; kept nullable and unused
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    member: Mapped["MemberProfile"] = relationship()

    def visible_to(self, user) -> bool:
        """Published reports are lab-visible; drafts stay private to the author."""
        if user.member_profile and user.member_profile.id == self.member_id:
            return True
        if user.role in ("PI", "TEACHER", "STUDENT"):
            return self.status == "published"
        return False


class WeeklyReportComment(Base, TimestampMixin):
    __tablename__ = "weekly_report_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("weekly_reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(String(2000), nullable=False)

    user: Mapped["User"] = relationship()
