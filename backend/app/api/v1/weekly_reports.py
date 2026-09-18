from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok, paged
from app.core.time import utcnow
from app.database import get_db
from app.models.enums import REPORT_STATUSES, ReportStatus, Role
from app.models.report import WeeklyReport
from app.models.user import MemberProfile, User
from app.permissions import is_staff
from app.schemas.report import (
    ReviewActionRequest,
    WeeklyReportCreate,
    WeeklyReportOut,
    WeeklyReportUpdate,
)
from app.services.notifications import create_notification

router = APIRouter(prefix="/weekly-reports", tags=["weekly-reports"])


def _out(report: WeeklyReport) -> dict:
    return WeeklyReportOut.model_validate(report).model_dump()


def _require_own_member(user: User) -> int:
    if not user.member_profile:
        raise HTTPException(
            status_code=400, detail="当前用户没有成员档案，无法提交周报"
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
    if is_staff(user):
        return
    if user.member_profile is None or user.member_profile.id != report.member_id:
        raise HTTPException(status_code=403, detail="没有查看该周报的权限")


def _reviewer_ids(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(User.id).where(
                User.role.in_([Role.PI, Role.TEACHER]), User.status == "active"
            )
        )
    )


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
    if user.role == Role.EQUIPMENT_ADMIN:
        raise HTTPException(status_code=403, detail="设备管理员无权访问周报模块")
    if not is_staff(user):
        profile = user.member_profile
        if not profile:
            raise HTTPException(status_code=403, detail="没有成员档案")
        if member_id is not None and member_id != profile.id:
            raise HTTPException(status_code=403, detail="只能查看自己的周报")
        member_id = profile.id

    stmt = select(WeeklyReport).options(
        joinedload(WeeklyReport.member).joinedload(MemberProfile.user)
    )
    if member_id:
        stmt = stmt.where(WeeklyReport.member_id == member_id)
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
            status_code=409, detail="该周已有周报，每人每周只能提交一份"
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
    from app.core.time import week_start_of

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
    return ok(item)


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
    if report.status not in (ReportStatus.DRAFT, ReportStatus.RETURNED):
        raise HTTPException(
            status_code=400, detail="周报已提交，不能修改（如需修改请联系老师退回）"
        )
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(report, field, value)
    write_audit_log(db, user, "update_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(_out(report), message="周报已更新")


@router.post("/{report_id}/submit")
def submit_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = _get_report(db, report_id)
    member_id = _require_own_member(user)
    if report.member_id != member_id:
        raise HTTPException(status_code=403, detail="只能提交自己的周报")
    if report.status not in (ReportStatus.DRAFT, ReportStatus.RETURNED):
        raise HTTPException(status_code=400, detail="当前状态不能提交")
    report.status = ReportStatus.SUBMITTED
    report.submitted_at = utcnow()
    for reviewer_id in _reviewer_ids(db):
        create_notification(
            db,
            reviewer_id,
            "report_submitted",
            "收到新的周报",
            f"{user.name} 提交了 {report.week_start} 周报，待审核",
            "weekly_report",
            report.id,
        )
    write_audit_log(db, user, "submit_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(_out(report), message="周报已提交")


@router.post("/{report_id}/review")
def review_report(
    report_id: int,
    body: ReviewActionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not is_staff(user):
        raise HTTPException(status_code=403, detail="只有 PI/教师可以审核周报")
    report = _get_report(db, report_id)
    if report.status != ReportStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="只有待审核状态的周报可以审核")
    report.status = ReportStatus.REVIEWED
    report.reviewed_at = utcnow()
    report.reviewer_id = user.id
    report.review_comment = body.comment
    if report.member and report.member.user_id:
        create_notification(
            db,
            report.member.user_id,
            "report_reviewed",
            "周报已审核",
            f"{user.name} 审核了你的 {report.week_start} 周报"
            + ("，查看导师意见" if body.comment else ""),
            "weekly_report",
            report.id,
        )
    write_audit_log(db, user, "review_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(_out(report), message="周报审核完成")


@router.post("/{report_id}/return")
def return_report(
    report_id: int,
    body: ReviewActionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not is_staff(user):
        raise HTTPException(status_code=403, detail="只有 PI/教师可以退回周报")
    report = _get_report(db, report_id)
    if report.status != ReportStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="只有待审核状态的周报可以退回")
    report.status = ReportStatus.RETURNED
    report.reviewed_at = utcnow()
    report.reviewer_id = user.id
    report.review_comment = body.comment
    if report.member and report.member.user_id:
        create_notification(
            db,
            report.member.user_id,
            "report_returned",
            "周报被退回",
            f"{user.name} 退回了你的 {report.week_start} 周报，请修改后重新提交",
            "weekly_report",
            report.id,
        )
    write_audit_log(db, user, "return_weekly_report", "weekly_report", report.id)
    db.commit()
    return ok(_out(report), message="周报已退回")
