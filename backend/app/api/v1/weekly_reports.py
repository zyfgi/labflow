"""Weekly reports — light process: draft -> publish, no review workflow.

An author writes a draft, publishes it (the whole lab can then read it), and
may keep editing even after publishing; every publish/update notifies the
configured audience and is audited. Teachers and peers give feedback through
comments instead of approve/return decisions.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok, paged
from app.core.time import utcnow, week_start_of
from app.database import get_db
from app.models.enums import REPORT_STATUSES, ReportStatus, Role
from app.models.report import WeeklyReport, WeeklyReportComment
from app.models.user import MemberProfile, User
from app.schemas.report import (
    WeeklyReportCommentCreate,
    WeeklyReportCreate,
    WeeklyReportOut,
    WeeklyReportUpdate,
)
from app.services.notifications import (
    notify,
    weekly_report_audience_ids,
)

router = APIRouter(prefix="/weekly-reports", tags=["weekly-reports"])


def _out(report: WeeklyReport) -> dict:
    return WeeklyReportOut.model_validate(report).model_dump()


def _require_own_member(user: User) -> int:
    if not user.member_profile:
        raise HTTPException(
            status_code=400, detail="当前用户没有成员档案，无法填写周报"
        )
    return user.member_profile.id


def _get_report(db: Session, report_id: int) -> WeeklyReport:
    report = db.scalar(
        select(WeeklyReport)
        .options(joinedload(WeeklyReport.member).joinedload(MemberProfile.user))
        .where(WeeklyReport.id == report_id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="周报不存在")
    return report


def _ensure_can_view(user: User, report: WeeklyReport) -> None:
    # read collaboration: published reports are lab-visible, drafts stay private
    if not report.visible_to(user):
        raise HTTPException(status_code=403, detail="没有查看该周报的权限")


@router.get("")
def list_reports(
    member_id: int | None = None,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if status and status not in REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="无效的周报状态")
    if user.role in (Role.EQUIPMENT_ADMIN, Role.GUEST):
        raise HTTPException(status_code=403, detail="无权访问周报模块")

    profile = user.member_profile
    is_student = user.role == Role.STUDENT
    if is_student and profile is None:
        raise HTTPException(status_code=403, detail="没有成员档案")

    stmt = select(WeeklyReport).options(
        joinedload(WeeklyReport.member).joinedload(MemberProfile.user)
    )
    if member_id is not None:
        own = profile is not None and member_id == profile.id
        stmt = stmt.where(WeeklyReport.member_id == member_id)
        if is_student and not own:
            stmt = stmt.where(WeeklyReport.status == ReportStatus.PUBLISHED)
    elif is_student:
        # read collaboration: everyone's published reports plus all of mine
        stmt = stmt.where(
            (WeeklyReport.status == ReportStatus.PUBLISHED)
            | (WeeklyReport.member_id == profile.id)
        )
    if status:
        stmt = stmt.where(WeeklyReport.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(WeeklyReport.week_start.desc(), WeeklyReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for r in rows:
        item = _out(r)
        item["member_name"] = r.member.user.name if r.member and r.member.user else None
        items.append(item)
    return paged(items, total, page, page_size)


@router.post("", status_code=201)
def create_report(
    body: WeeklyReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    member_id = _require_own_member(user)
    week_end = body.week_start + timedelta(days=6)
    existing = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.member_id == member_id,
            WeeklyReport.week_start == body.week_start,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="该周已有周报，每人每周只能填写一份"
        )

    report = WeeklyReport(
        member_id=member_id,
        week_start=body.week_start,
        week_end=week_end,
        status=ReportStatus.DRAFT,
        **body.model_dump(exclude={"week_start"}),
    )
    db.add(report)
    db.flush()
    write_audit_log(db, user, "create_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(_out(report), message="周报草稿已创建")


@router.get("/me/current")
def my_current_week_report(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    member_id = _require_own_member(user)
    week_start = week_start_of()
    report = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.member_id == member_id, WeeklyReport.week_start == week_start
        )
    )
    return ok(_out(report) if report else None)


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_report(db, report_id)
    _ensure_can_view(user, report)
    item = _out(report)
    if report.member and report.member.user:
        item["member_name"] = report.member.user.name
    item["comments"] = _comments_payload(db, report.id)
    return ok(item)


def _comments_payload(db: Session, report_id: int) -> list[dict]:
    rows = db.scalars(
        select(WeeklyReportComment)
        .options(joinedload(WeeklyReportComment.user))
        .where(WeeklyReportComment.report_id == report_id)
        .order_by(WeeklyReportComment.created_at)
    ).all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "user_name": c.user.name if c.user else None,
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]


@router.patch("/{report_id}")
def update_report(
    report_id: int,
    body: WeeklyReportUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_report(db, report_id)
    member_id = _require_own_member(user)
    if report.member_id != member_id:
        raise HTTPException(status_code=403, detail="只能修改自己的周报")
    data = body.model_dump(exclude_unset=True)
    was_published = report.status == ReportStatus.PUBLISHED
    for field, value in data.items():
        setattr(report, field, value)
    write_audit_log(
        db,
        user,
        "update_weekly_report",
        "weekly_report",
        report.id,
        {"fields": list(data.keys()), "published": was_published},
    )
    if was_published:
        # published reports stay published; followers just hear about the update
        notify(
            db,
            weekly_report_audience_ids(db, user.id),
            "weekly_report_updated",
            "周报更新",
            f"{user.name} 更新了 {report.week_start} 周报",
            "weekly_report",
            report.id,
            exclude_user_id=user.id,
        )
    db.commit()
    return ok(
        _out(report), message="周报已更新" + ("，已通知关注人" if was_published else "")
    )


@router.post("/{report_id}/publish")
def publish_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_report(db, report_id)
    member_id = _require_own_member(user)
    if report.member_id != member_id:
        raise HTTPException(status_code=403, detail="只能发布自己的周报")
    if report.status == ReportStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="周报已发布")
    report.status = ReportStatus.PUBLISHED
    report.published_at = utcnow()
    write_audit_log(db, user, "publish_weekly_report", "weekly_report", report.id)
    notify(
        db,
        weekly_report_audience_ids(db, user.id),
        "weekly_report_published",
        "周报发布",
        f"{user.name} 发布了 {report.week_start} 周报",
        "weekly_report",
        report.id,
        exclude_user_id=user.id,
    )
    db.commit()
    return ok(_out(report), message="周报已发布，实验室成员可见")


@router.post("/{report_id}/comments", status_code=201)
def add_comment(
    report_id: int,
    body: WeeklyReportCommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role in (Role.EQUIPMENT_ADMIN, Role.GUEST):
        raise HTTPException(status_code=403, detail="无权评论周报")
    report = _get_report(db, report_id)
    _ensure_can_view(user, report)
    comment = WeeklyReportComment(
        report_id=report.id, user_id=user.id, content=body.content
    )
    db.add(comment)
    db.flush()
    author_user_id = report.member.user_id if report.member else None
    notify(
        db,
        [author_user_id],
        "weekly_report_commented",
        "周报收到评论",
        f"{user.name} 评论了你的 {report.week_start} 周报",
        "weekly_report",
        report.id,
        exclude_user_id=user.id,
    )
    write_audit_log(db, user, "comment_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(
        {
            "id": comment.id,
            "report_id": report.id,
            "user_id": user.id,
            "user_name": user.name,
            "content": comment.content,
            "created_at": comment.created_at.isoformat()
            if comment.created_at
            else None,
        },
        message="评论已添加",
    )
