"""CSV / XLSX exports, permission-controlled."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, write_audit_log
from app.core.time import utcnow
from app.database import get_db
from app.models.equipment import Equipment, EquipmentBooking
from app.models.project import Task
from app.models.report import WeeklyReport
from app.models.user import MemberProfile, User

router = APIRouter(prefix="/exports", tags=["exports"])


def _require(user: User, roles: tuple) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="没有导出该数据的权限")


def _csv_response(rows: list[list], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    data = io.BytesIO(
        buf.getvalue().encode("utf-8-sig")
    )  # BOM so Excel opens UTF-8 correctly
    return StreamingResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _xlsx_response(rows: list[list], filename: str) -> StreamingResponse:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "export"
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


EXPORTS = {
    "members": ("members", ("PI", "TEACHER")),
    "weekly-reports": ("weekly_reports", ("PI", "TEACHER")),
    "tasks": ("tasks", ("PI", "TEACHER")),
    "equipment": ("equipment", ("PI", "EQUIPMENT_ADMIN")),
    "equipment-bookings": ("equipment_bookings", ("PI", "EQUIPMENT_ADMIN")),
}

HEADERS = {
    "members": [
        "ID",
        "姓名",
        "用户名",
        "邮箱",
        "身份",
        "年级",
        "学号",
        "研究方向",
        "状态",
        "入组日期",
    ],
    "weekly-reports": [
        "ID",
        "成员",
        "周起始",
        "周结束",
        "状态",
        "本周工作",
        "问题",
        "下周计划",
        "自评进度",
        "导师意见",
    ],
    "tasks": [
        "ID",
        "任务",
        "项目",
        "负责人",
        "状态",
        "优先级",
        "截止日期",
        "进度",
        "创建时间",
    ],
    "equipment": ["资产编号", "名称", "分类", "厂商", "型号", "位置", "状态", "管理员"],
    "equipment-bookings": ["ID", "设备", "预约人", "开始", "结束", "用途", "状态"],
}


@router.get("/{kind}")
def export(
    kind: str,
    format: str = "csv",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    if kind not in EXPORTS:
        raise HTTPException(status_code=404, detail="未知的导出类型")
    label, roles = EXPORTS[kind]
    _require(user, roles)
    if format not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="format 仅支持 csv / xlsx")

    rows: list[list] = [HEADERS[kind]]
    stamp = utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"labflow_{label}_{stamp}.{format}"

    if kind == "members":
        for m in db.scalars(
            select(MemberProfile)
            .options(joinedload(MemberProfile.user))
            .order_by(MemberProfile.id)
        ).all():
            u = m.user
            rows.append(
                [
                    m.id,
                    u.name if u else "",
                    u.username if u else "",
                    u.email if u else "",
                    m.member_type,
                    m.grade_year or "",
                    m.student_no or "",
                    m.research_direction or "",
                    m.status,
                    m.join_date.isoformat() if m.join_date else "",
                ]
            )
    elif kind == "weekly-reports":
        for r in db.scalars(
            select(WeeklyReport)
            .options(joinedload(WeeklyReport.member).joinedload(MemberProfile.user))
            .order_by(WeeklyReport.week_start.desc())
        ).all():
            name = r.member.user.name if r.member and r.member.user else ""
            rows.append(
                [
                    r.id,
                    name,
                    r.week_start.isoformat(),
                    r.week_end.isoformat(),
                    r.status,
                    (r.work_summary or "").replace("\n", " "),
                    (r.problems or "").replace("\n", " "),
                    (r.next_week_plan or "").replace("\n", " "),
                    r.self_progress,
                    (r.review_comment or "").replace("\n", " "),
                ]
            )
    elif kind == "tasks":
        for t in db.scalars(
            select(Task)
            .options(joinedload(Task.project))
            .where(Task.deleted_at.is_(None))
        ).all():
            assignee = db.get(User, t.assignee_id) if t.assignee_id else None
            rows.append(
                [
                    t.id,
                    t.title,
                    t.project.name if t.project else "",
                    assignee.name if assignee else "",
                    t.status,
                    t.priority,
                    t.due_date.isoformat() if t.due_date else "",
                    t.progress,
                    t.created_at.strftime("%Y-%m-%d %H:%M"),
                ]
            )
    elif kind == "equipment":
        for e in db.scalars(
            select(Equipment).where(Equipment.deleted_at.is_(None))
        ).all():
            manager = db.get(User, e.manager_id) if e.manager_id else None
            rows.append(
                [
                    e.asset_no,
                    e.name,
                    e.category,
                    e.manufacturer or "",
                    e.model or "",
                    e.location or "",
                    e.status,
                    manager.name if manager else "",
                ]
            )
    elif kind == "equipment-bookings":
        for b in db.scalars(
            select(EquipmentBooking)
            .options(joinedload(EquipmentBooking.user))
            .order_by(EquipmentBooking.start_time.desc())
        ).all():
            eq = db.get(Equipment, b.equipment_id)
            rows.append(
                [
                    b.id,
                    eq.name if eq else "",
                    b.user.name if b.user else "",
                    b.start_time.strftime("%Y-%m-%d %H:%M"),
                    b.end_time.strftime("%Y-%m-%d %H:%M"),
                    b.purpose or "",
                    b.status,
                ]
            )

    write_audit_log(db, user, "export_data", "export", kind, {"format": format})
    db.commit()

    return (
        _xlsx_response(rows, filename)
        if format == "xlsx"
        else _csv_response(rows, filename)
    )
