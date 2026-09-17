from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    pass


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="STUDENT", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    member_profile: Mapped["MemberProfile | None"] = relationship(
        back_populates="user", uselist=False, lazy="joined"
    )


class MemberProfile(Base, TimestampMixin):
    __tablename__ = "member_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    student_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    member_type: Mapped[str] = mapped_column(String(20), default="master", index=True, nullable=False)
    grade_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    research_direction: Mapped[str | None] = mapped_column(String(200), nullable=True)
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_leave_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supervisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("member_profiles.id", ondelete="SET NULL"), nullable=True
    )
    office_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="member_profile")
