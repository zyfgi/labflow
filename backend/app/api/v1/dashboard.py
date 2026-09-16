"""PI and Student dashboards. Every number is a live database query."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.responses import ok
from app.database import get_db
from app.models.equipment import (
    Equipment,
    EquipmentBooking,
    EquipmentMaintenance,
)
from app.models.enums import (
    BookingStatus,
    BorrowStatus,
    EquipmentStatus,
    ExperimentStatus,
    MaintenanceStatus,
    ReportStatus,
    TaskStatus,
)
from app.models.experiment import Experiment
from app.models.project import Milestone, Project, ProjectMember, Task
from app.models.report import WeeklyReport
from app.models.system import Notification
from app.models.user import MemberProfile, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

OPEN_TASK_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.REVIEW)


def _week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/pi")
def pi_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role not in ("PI", "TEACHER"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="该看板仅对 PI/教师开放")

    today = date.today()
    week_start = _week_start()

    # ---- KPIs ----
    member_total = db.scalar(
        select(func.count()).select_from(MemberProfile).where(MemberProfile.status == "active")
    ) or 0
    active_projects = db.scalar(
        select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None), Project.status == "active"
        )
    ) or 0

    student_ids = db.scalars(
        select(User.id).where(User.role == "STUDENT", User.status == "active")
    ).all()
    student_member_ids = db.scalars(
        select(MemberProfile.id).where(
            MemberProfile.user_id.in_(student_ids or [0]), MemberProfile.status == "active"
        )
    ).all()
    submitted_count = 0
    if student_member_ids:
        submitted_count = db.scalar(
            select(func.count()).select_from(WeeklyReport).where(
                WeeklyReport.member_id.in_(student_member_ids),
                WeeklyReport.week_start == week_start,
                WeeklyReport.status.in_((ReportStatus.SUBMITTED, ReportStatus.REVIEWED)),
            )
        ) or 0
    report_rate = round(submitted_count * 100 / len(student_member_ids)) if student_member_ids else 0

    open_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES)
        )
    ) or 0
    overdue_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.deleted_at.is_(None),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_date < today,
        )
    ) or 0
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    experiments_this_week = db.scalar(
        select(func.count()).select_from(Experiment).where(
            Experiment.deleted_at.is_(None), Experiment.created_at >= week_start_dt
        )
    ) or 0
    equipment_fault = db.scalar(
        select(func.count()).select_from(Equipment).where(
            Equipment.deleted_at.is_(None),
            Equipment.status.in_((EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE)),
        )
    ) or 0
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)
    bookings_today = db.scalar(
        select(func.count()).select_from(EquipmentBooking).where(
            EquipmentBooking.status == BookingStatus.APPROVED,
            EquipmentBooking.start_time < tomorrow_start,
            EquipmentBooking.end_time > today_start,
        )
    ) or 0

    kpis = {
        "member_total": member_total,
        "active_projects": active_projects,
        "weekly_report_rate": report_rate,
        "weekly_report_submitted": submitted_count,
        "weekly_report_expected": len(student_member_ids),
        "tasks_open": open_tasks,
        "tasks_overdue": overdue_tasks,
        "experiments_this_week": experiments_this_week,
        "equipment_fault": equipment_fault,
        "bookings_today": bookings_today,
    }

    # ---- member progress ----
    members = db.scalars(
        select(MemberProfile).options(joinedload(MemberProfile.user)).where(MemberProfile.status == "active")
    ).all()
    member_rows = []
    for m in members:
        proj_ids = db.scalars(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == m.user_id, ProjectMember.left_at.is_(None)
            )
        ).all()
        projects = db.scalars(
            select(Project).where(
                Project.id.in_(proj_ids or [0]),
                Project.deleted_at.is_(None),
                Project.status.in_(("planning", "active", "paused")),
            )
        ).all() if proj_ids else []
        in_progress = db.scalar(
            select(func.count()).select_from(Task).where(
                Task.assignee_id == m.user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES)
            )
        ) or 0
        overdue = db.scalar(
            select(func.count()).select_from(Task).where(
                Task.assignee_id == m.user_id,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_date < today,
            )
        ) or 0
        report = db.scalar(
            select(WeeklyReport).where(
                WeeklyReport.member_id == m.id, WeeklyReport.week_start == week_start
            )
        )
        latest_exp = db.scalar(
            select(func.max(Experiment.experiment_date)).where(
                Experiment.owner_id == m.user_id, Experiment.deleted_at.is_(None)
            )
        )
        member_rows.append(
            {
                "member_id": m.id,
                "name": m.user.name if m.user else None,
                "member_type": m.member_type,
                "research_direction": m.research_direction,
                "projects": [p.name for p in projects],
                "in_progress_tasks": in_progress,
                "overdue_tasks": overdue,
                "this_week_report": report.status if report else "none",
                "latest_experiment_date": latest_exp.isoformat() if latest_exp else None,
            }
        )

    # ---- project progress ----
    projects = db.scalars(
        select(Project)
        .where(Project.deleted_at.is_(None), Project.status.in_(("planning", "active", "paused")))
        .order_by(Project.priority.desc(), Project.updated_at.desc())
        .limit(12)
    ).all()
    project_rows = []
    for p in projects:
        owner = db.get(User, p.owner_id) if p.owner_id else None
        done = db.scalar(
            select(func.count()).select_from(Task).where(
                Task.project_id == p.id, Task.deleted_at.is_(None), Task.status == TaskStatus.DONE
            )
        ) or 0
        total = db.scalar(
            select(func.count()).select_from(Task).where(Task.project_id == p.id, Task.deleted_at.is_(None))
        ) or 0
        overdue = db.scalar(
            select(func.count()).select_from(Task).where(
                Task.project_id == p.id,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_date < today,
            )
        ) or 0
        next_milestone = db.scalar(
            select(Milestone).where(
                Milestone.project_id == p.id,
                Milestone.status != "completed",
                Milestone.due_date.is_not(None),
            ).order_by(Milestone.due_date)
        )
        project_rows.append(
            {
                "id": p.id,
                "name": p.name,
                "owner_name": owner.name if owner else None,
                "status": p.status,
                "progress": p.progress,
                "task_done": done,
                "task_total": total,
                "overdue_tasks": overdue,
                "next_milestone": (
                    {"title": next_milestone.title, "due_date": next_milestone.due_date.isoformat()}
                    if next_milestone
                    else None
                ),
            }
        )

    # ---- pending items ----
    pending_reports = db.scalar(
        select(func.count()).select_from(WeeklyReport).where(WeeklyReport.status == ReportStatus.SUBMITTED)
    ) or 0
    pending_bookings = db.scalar(
        select(func.count()).select_from(EquipmentBooking).where(
            EquipmentBooking.status == BookingStatus.PENDING
        )
    ) or 0
    fault_equipment = db.scalars(
        select(Equipment).where(
            Equipment.deleted_at.is_(None),
            Equipment.status.in_((EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE)),
        )
    ).all()
    due_milestones = db.scalars(
        select(Milestone)
        .options(joinedload(Milestone.project))
        .where(
            Milestone.status != "completed",
            Milestone.due_date.is_not(None),
            Milestone.due_date <= today + timedelta(days=14),
        )
        .order_by(Milestone.due_date)
        .limit(8)
    ).all()
    overdue_task_rows = db.scalars(
        select(Task).where(
            Task.deleted_at.is_(None),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_date < today,
        ).order_by(Task.due_date)
        .limit(8)
    ).all()

    todo = {
        "pending_reports": pending_reports,
        "pending_bookings": pending_bookings,
        "overdue_tasks": [
            {"id": t.id, "title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None}
            for t in overdue_task_rows
        ],
        "fault_equipment": [
            {"id": e.id, "name": e.name, "status": e.status, "asset_no": e.asset_no} for e in fault_equipment
        ],
        "due_milestones": [
            {
                "id": m.id,
                "title": m.title,
                "project_name": m.project.name if m.project else None,
                "due_date": m.due_date.isoformat() if m.due_date else None,
            }
            for m in due_milestones
        ],
    }

    # ---- recent activity ----
    activity = []
    for exp in db.scalars(
        select(Experiment).options(joinedload(Experiment.owner_ref)).where(Experiment.deleted_at.is_(None))
        .order_by(Experiment.created_at.desc()).limit(5)
    ):
        activity.append(
            {"time": exp.created_at.isoformat(), "type": "experiment",
             "text": f"{exp.owner_ref.name if exp.owner_ref else ''} 创建实验 {exp.experiment_no}「{exp.title}」"}
        )
    for r in db.scalars(
        select(WeeklyReport).options(joinedload(WeeklyReport.member).joinedload(MemberProfile.user))
        .where(WeeklyReport.status.in_((ReportStatus.SUBMITTED, ReportStatus.REVIEWED)))
        .order_by(WeeklyReport.updated_at.desc()).limit(5)
    ):
        name = r.member.user.name if r.member and r.member.user else ""
        action = "提交" if r.status == ReportStatus.SUBMITTED else "的周报被审核"
        activity.append(
            {"time": (r.submitted_at or r.updated_at).isoformat(), "type": "report",
             "text": f"{name} {action} {r.week_start} 周报"}
        )
    for t in db.scalars(
        select(Task).where(Task.status == TaskStatus.DONE, Task.completed_at.is_not(None))
        .order_by(Task.completed_at.desc()).limit(5)
    ):
        activity.append(
            {"time": t.completed_at.isoformat(), "type": "task", "text": f"任务「{t.title}」完成"}
        )
    for m in db.scalars(
        select(EquipmentMaintenance).order_by(EquipmentMaintenance.reported_at.desc()).limit(3)
    ):
        eq = db.get(Equipment, m.equipment_id)
        if eq:
            activity.append(
                {"time": (m.reported_at or m.created_at).isoformat(), "type": "equipment",
                 "text": f"设备「{eq.name}」进入{ '维修' if m.status == MaintenanceStatus.PROCESSING else '上报'}状态"}
            )
    activity.sort(key=lambda a: a["time"], reverse=True)
    activity = activity[:10]

    return ok(
        {
            "kpis": kpis,
            "members": member_rows,
            "projects": project_rows,
            "todo": todo,
            "activity": activity,
        }
    )


@router.get("/student")
def student_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    today = date.today()
    week_start = _week_start()
    uid = user.id

    in_progress = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assignee_id == uid, Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES)
        )
    ) or 0
    overdue = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.assignee_id == uid,
            Task.deleted_at.is_(None),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_date < today,
        )
    ) or 0

    my_member_id = user.member_profile.id if user.member_profile else None
    report = None
    if my_member_id:
        report = db.scalar(
            select(WeeklyReport).where(
                WeeklyReport.member_id == my_member_id, WeeklyReport.week_start == week_start
            )
        )
    my_experiments = db.scalar(
        select(func.count()).select_from(Experiment).where(
            Experiment.owner_id == uid, Experiment.deleted_at.is_(None)
        )
    ) or 0

    upcoming_bookings = db.scalars(
        select(EquipmentBooking).where(
            EquipmentBooking.user_id == uid,
            EquipmentBooking.status == BookingStatus.APPROVED,
            EquipmentBooking.end_time > _utcnow(),
        ).order_by(EquipmentBooking.start_time).limit(5)
    ).all()
    booking_rows = []
    for b in upcoming_bookings:
        eq = db.get(Equipment, b.equipment_id)
        booking_rows.append(
            {
                "id": b.id,
                "equipment_name": eq.name if eq else None,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
            }
        )

    my_tasks = db.scalars(
        select(Task).where(
            Task.assignee_id == uid, Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES)
        ).order_by(Task.due_date.asc().nullslast()).limit(8)
    ).all()
    task_rows = []
    for t in my_tasks:
        proj = db.get(Project, t.project_id)
        task_rows.append(
            {
                "id": t.id,
                "title": t.title,
                "project_name": proj.name if proj else None,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "progress": t.progress,
                "is_overdue": bool(t.due_date and t.due_date < today),
            }
        )

    recent_experiments = db.scalars(
        select(Experiment).where(Experiment.owner_id == uid, Experiment.deleted_at.is_(None))
        .order_by(Experiment.updated_at.desc()).limit(5)
    ).all()

    unread_notifications = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == uid, Notification.is_read.is_(False)
        )
    ) or 0

    my_projects = []
    proj_ids = db.scalars(
        select(ProjectMember.project_id).where(
            ProjectMember.user_id == uid, ProjectMember.left_at.is_(None)
        )
    ).all()
    for p in db.scalars(
        select(Project).where(Project.id.in_(proj_ids or [0]), Project.deleted_at.is_(None))
    ).all():
        my_projects.append({"id": p.id, "name": p.name, "status": p.status, "progress": p.progress})

    return ok(
        {
            "kpis": {
                "tasks_in_progress": in_progress,
                "tasks_overdue": overdue,
                "this_week_report": report.status if report else "none",
                "experiment_count": my_experiments,
                "unread_notifications": unread_notifications,
            },
            "tasks": task_rows,
            "bookings": booking_rows,
            "projects": my_projects,
            "experiments": [
                {
                    "id": e.id,
                    "experiment_no": e.experiment_no,
                    "title": e.title,
                    "status": e.status,
                    "experiment_date": e.experiment_date.isoformat() if e.experiment_date else None,
                }
                for e in recent_experiments
            ],
        }
    )
