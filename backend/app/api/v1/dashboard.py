"""PI and Student dashboards. Every number is a live database query."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.core.responses import ok
from app.core.time import app_today, utcnow, week_start_of
from app.database import get_db
from app.models.enums import (
    BookingStatus,
    BorrowStatus,
    EquipmentStatus,
    MaintenanceStatus,
    ReportStatus,
    TaskStatus,
)
from app.models.equipment import (
    Equipment,
    EquipmentBooking,
    EquipmentBorrow,
    EquipmentMaintenance,
)
from app.models.experiment import Experiment
from app.models.project import Milestone, Project, ProjectMember, Task
from app.models.report import WeeklyReport
from app.models.system import Notification
from app.models.user import MemberProfile, User
from app.services.lookups import id_name_map

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

OPEN_TASK_STATUSES = (
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.BLOCKED,
)


@router.get("/pi")
def pi_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role not in ("PI", "TEACHER"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="该看板仅对 PI/教师开放")

    today = app_today()
    week_start = week_start_of()

    # ---- KPIs ----
    member_total = (
        db.scalar(
            select(func.count())
            .select_from(MemberProfile)
            .where(MemberProfile.status == "active")
        )
        or 0
    )
    active_projects = (
        db.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.deleted_at.is_(None), Project.status == "active")
        )
        or 0
    )

    student_ids = db.scalars(
        select(User.id).where(User.role == "STUDENT", User.status == "active")
    ).all()
    student_member_ids = db.scalars(
        select(MemberProfile.id).where(
            MemberProfile.user_id.in_(student_ids or [0]),
            MemberProfile.status == "active",
        )
    ).all()
    submitted_count = 0
    if student_member_ids:
        submitted_count = (
            db.scalar(
                select(func.count())
                .select_from(WeeklyReport)
                .where(
                    WeeklyReport.member_id.in_(student_member_ids),
                    WeeklyReport.week_start == week_start,
                    WeeklyReport.status == ReportStatus.PUBLISHED,
                )
            )
            or 0
        )
    report_rate = (
        round(submitted_count * 100 / len(student_member_ids))
        if student_member_ids
        else 0
    )

    open_tasks = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES))
        )
        or 0
    )
    overdue_tasks = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_date < today,
            )
        )
        or 0
    )
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    experiments_this_week = (
        db.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(
                Experiment.deleted_at.is_(None), Experiment.created_at >= week_start_dt
            )
        )
        or 0
    )
    equipment_fault = (
        db.scalar(
            select(func.count())
            .select_from(Equipment)
            .where(
                Equipment.deleted_at.is_(None),
                Equipment.status.in_(
                    (EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE)
                ),
            )
        )
        or 0
    )
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)
    bookings_today = (
        db.scalar(
            select(func.count())
            .select_from(EquipmentBooking)
            .where(
                EquipmentBooking.status == BookingStatus.RESERVED,
                EquipmentBooking.start_time < tomorrow_start,
                EquipmentBooking.end_time > today_start,
            )
        )
        or 0
    )

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

    # ---- member progress (set-based: 5 aggregate queries total) ----
    members = db.scalars(
        select(MemberProfile)
        .options(joinedload(MemberProfile.user))
        .where(MemberProfile.status == "active")
    ).all()
    member_user_ids = [m.user_id for m in members]

    open_cond = Task.status.in_(OPEN_TASK_STATUSES)
    task_rows = db.execute(
        select(
            Task.assignee_id,
            func.count().label("open"),
            func.sum(case((Task.due_date < today, 1), else_=0)).label("overdue"),
        )
        .where(
            Task.deleted_at.is_(None),
            open_cond,
            Task.assignee_id.in_(member_user_ids or [0]),
        )
        .group_by(Task.assignee_id)
    ).all()
    task_by_user = {r[0]: (r[1] or 0, r[2] or 0) for r in task_rows}

    report_rows = db.execute(
        select(WeeklyReport.member_id, WeeklyReport.status).where(
            WeeklyReport.member_id.in_([m.id for m in members] or [0]),
            WeeklyReport.week_start == week_start,
        )
    ).all()
    report_by_member = {r[0]: r[1] for r in report_rows}

    exp_rows = db.execute(
        select(Experiment.owner_id, func.max(Experiment.experiment_date))
        .where(
            Experiment.deleted_at.is_(None),
            Experiment.owner_id.in_(member_user_ids or [0]),
        )
        .group_by(Experiment.owner_id)
    ).all()
    exp_by_user = {r[0]: r[1] for r in exp_rows}

    pm_rows = db.execute(
        select(ProjectMember.user_id, Project.id, Project.name)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.left_at.is_(None),
            ProjectMember.user_id.in_(member_user_ids or [0]),
            Project.deleted_at.is_(None),
            Project.status.in_(("planning", "active", "paused")),
        )
    ).all()
    projects_by_user: dict[int, list[tuple[int, str]]] = {}
    for uid, pid, pname in pm_rows:
        projects_by_user.setdefault(uid, []).append((pid, pname))

    member_rows = []
    for m in members:
        open_n, overdue_n = task_by_user.get(m.user_id, (0, 0))
        m_projects = projects_by_user.get(m.user_id, [])
        latest_exp = exp_by_user.get(m.user_id)
        member_rows.append(
            {
                "member_id": m.id,
                "name": m.user.name if m.user else None,
                "member_type": m.member_type,
                "research_direction": m.research_direction,
                "projects": [name for _, name in m_projects],
                "in_progress_tasks": open_n,
                "overdue_tasks": overdue_n,
                "this_week_report": report_by_member.get(m.id, "none"),
                "latest_experiment_date": latest_exp.isoformat()
                if latest_exp
                else None,
            }
        )

    # ---- project progress (set-based: 4 queries total) ----
    projects = db.scalars(
        select(Project)
        .where(
            Project.deleted_at.is_(None),
            Project.status.in_(("planning", "active", "paused")),
        )
        .order_by(Project.priority.desc(), Project.updated_at.desc())
        .limit(12)
    ).all()
    project_ids = [p.id for p in projects]
    owner_names = id_name_map(db, User.id, User.name, {p.owner_id for p in projects})

    ptask_rows = db.execute(
        select(
            Task.project_id,
            func.count().label("total"),
            func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)).label("done"),
            func.sum(
                case(
                    (Task.status.in_(OPEN_TASK_STATUSES) & (Task.due_date < today), 1),
                    else_=0,
                )
            ).label("overdue"),
        )
        .where(Task.deleted_at.is_(None), Task.project_id.in_(project_ids or [0]))
        .group_by(Task.project_id)
    ).all()
    stats_by_project = {r[0]: (r[1] or 0, r[2] or 0, r[3] or 0) for r in ptask_rows}

    milestone_rows = db.scalars(
        select(Milestone)
        .where(
            Milestone.project_id.in_(project_ids or [0]),
            Milestone.status != "completed",
            Milestone.due_date.is_not(None),
        )
        .order_by(Milestone.due_date)
    ).all()
    next_milestone_by_project: dict[int, Milestone] = {}
    for ms in milestone_rows:
        next_milestone_by_project.setdefault(ms.project_id, ms)

    project_rows = []
    for p in projects:
        total_t, done_t, overdue_t = stats_by_project.get(p.id, (0, 0, 0))
        ms = next_milestone_by_project.get(p.id)
        project_rows.append(
            {
                "id": p.id,
                "name": p.name,
                "owner_name": owner_names.get(p.owner_id) if p.owner_id else None,
                "status": p.status,
                "progress": p.progress,
                "task_done": done_t,
                "task_total": total_t,
                "overdue_tasks": overdue_t,
                "next_milestone": (
                    {"title": ms.title, "due_date": ms.due_date.isoformat()}
                    if ms
                    else None
                ),
            }
        )

    # ---- attention items (提示，不阻断业务) ----
    fault_equipment = db.scalars(
        select(Equipment).where(
            Equipment.deleted_at.is_(None),
            Equipment.status.in_((EquipmentStatus.FAULT, EquipmentStatus.MAINTENANCE)),
        )
    ).all()
    overdue_borrow_rows = db.scalars(
        select(EquipmentBorrow)
        .where(
            EquipmentBorrow.status.in_((BorrowStatus.BORROWED, BorrowStatus.OVERDUE)),
            EquipmentBorrow.expected_return_time
            < datetime.combine(today, datetime.min.time()),
        )
        .order_by(EquipmentBorrow.expected_return_time)
        .limit(8)
    ).all()
    borrow_eq_names = id_name_map(
        db, Equipment.id, Equipment.name, {b.equipment_id for b in overdue_borrow_rows}
    )
    stale_cutoff = datetime.combine(today - timedelta(days=30), datetime.min.time())
    stale_projects = db.scalars(
        select(Project)
        .where(
            Project.deleted_at.is_(None),
            Project.status.in_(("planning", "active", "paused")),
            Project.updated_at < stale_cutoff,
        )
        .order_by(Project.updated_at)
        .limit(8)
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
        select(Task)
        .where(
            Task.deleted_at.is_(None),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_date < today,
        )
        .order_by(Task.due_date)
        .limit(8)
    ).all()

    attention = {
        "overdue_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in overdue_task_rows
        ],
        "overdue_borrows": [
            {
                "id": b.id,
                "equipment_name": borrow_eq_names.get(b.equipment_id),
                "expected_return_time": b.expected_return_time.isoformat()
                if b.expected_return_time
                else None,
            }
            for b in overdue_borrow_rows
        ],
        "fault_equipment": [
            {"id": e.id, "name": e.name, "status": e.status, "asset_no": e.asset_no}
            for e in fault_equipment
        ],
        "stale_projects": [
            {
                "id": p.id,
                "name": p.name,
                "updated_at": p.updated_at.isoformat(),
            }
            for p in stale_projects
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
        select(Experiment)
        .options(joinedload(Experiment.owner_ref))
        .where(Experiment.deleted_at.is_(None))
        .order_by(Experiment.created_at.desc())
        .limit(5)
    ):
        activity.append(
            {
                "time": exp.created_at.isoformat(),
                "type": "experiment",
                "text": f"{exp.owner_ref.name if exp.owner_ref else ''} 创建实验 {exp.experiment_no}「{exp.title}」",
            }
        )
    for r in db.scalars(
        select(WeeklyReport)
        .options(joinedload(WeeklyReport.member).joinedload(MemberProfile.user))
        .where(WeeklyReport.status == ReportStatus.PUBLISHED)
        .order_by(WeeklyReport.published_at.desc())
        .limit(5)
    ):
        name = r.member.user.name if r.member and r.member.user else ""
        activity.append(
            {
                "time": (r.published_at or r.updated_at).isoformat(),
                "type": "report",
                "text": f"{name} 发布了 {r.week_start} 周报",
            }
        )
    for t in db.scalars(
        select(Task)
        .where(Task.status == TaskStatus.DONE, Task.completed_at.is_not(None))
        .order_by(Task.completed_at.desc())
        .limit(5)
    ):
        activity.append(
            {
                "time": t.completed_at.isoformat(),
                "type": "task",
                "text": f"任务「{t.title}」完成",
            }
        )
    maintenance_rows = db.scalars(
        select(EquipmentMaintenance)
        .order_by(EquipmentMaintenance.reported_at.desc())
        .limit(3)
    ).all()
    maintenance_eq_names = id_name_map(
        db, Equipment.id, Equipment.name, {m.equipment_id for m in maintenance_rows}
    )
    for m in maintenance_rows:
        eq_name = maintenance_eq_names.get(m.equipment_id)
        if eq_name:
            activity.append(
                {
                    "time": (m.reported_at or m.created_at).isoformat(),
                    "type": "equipment",
                    "text": f"设备「{eq_name}」进入{'维修' if m.status == MaintenanceStatus.PROCESSING else '上报'}状态",
                }
            )
    activity.sort(key=lambda a: a["time"], reverse=True)
    activity = activity[:10]

    return ok(
        {
            "kpis": kpis,
            "members": member_rows,
            "projects": project_rows,
            "attention": attention,
            "activity": activity,
        }
    )


@router.get("/student")
def student_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    today = app_today()
    week_start = week_start_of()
    uid = user.id

    in_progress = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.assignee_id == uid,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
            )
        )
        or 0
    )
    overdue = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.assignee_id == uid,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_date < today,
            )
        )
        or 0
    )

    my_member_id = user.member_profile.id if user.member_profile else None
    report = None
    if my_member_id:
        report = db.scalar(
            select(WeeklyReport).where(
                WeeklyReport.member_id == my_member_id,
                WeeklyReport.week_start == week_start,
            )
        )
    my_experiments = (
        db.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(Experiment.owner_id == uid, Experiment.deleted_at.is_(None))
        )
        or 0
    )

    upcoming_bookings = db.scalars(
        select(EquipmentBooking)
        .where(
            EquipmentBooking.user_id == uid,
            EquipmentBooking.status == BookingStatus.RESERVED,
            EquipmentBooking.end_time > utcnow(),
        )
        .order_by(EquipmentBooking.start_time)
        .limit(5)
    ).all()
    booking_eq_names = id_name_map(
        db, Equipment.id, Equipment.name, {b.equipment_id for b in upcoming_bookings}
    )
    booking_rows = [
        {
            "id": b.id,
            "equipment_name": booking_eq_names.get(b.equipment_id),
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat(),
        }
        for b in upcoming_bookings
    ]

    my_tasks = db.scalars(
        select(Task)
        .where(
            Task.assignee_id == uid,
            Task.deleted_at.is_(None),
            Task.status.in_(OPEN_TASK_STATUSES),
        )
        .order_by(Task.due_date.asc().nullslast())
        .limit(8)
    ).all()
    task_project_names = id_name_map(
        db, Project.id, Project.name, {t.project_id for t in my_tasks}
    )
    task_rows = [
        {
            "id": t.id,
            "title": t.title,
            "project_name": task_project_names.get(t.project_id),
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "progress": t.progress,
            "is_overdue": bool(t.due_date and t.due_date < today),
        }
        for t in my_tasks
    ]

    recent_experiments = db.scalars(
        select(Experiment)
        .where(Experiment.owner_id == uid, Experiment.deleted_at.is_(None))
        .order_by(Experiment.updated_at.desc())
        .limit(5)
    ).all()

    unread_notifications = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == uid, Notification.is_read.is_(False))
        )
        or 0
    )

    my_projects = []
    proj_ids = db.scalars(
        select(ProjectMember.project_id).where(
            ProjectMember.user_id == uid, ProjectMember.left_at.is_(None)
        )
    ).all()
    for p in db.scalars(
        select(Project).where(
            Project.id.in_(proj_ids or [0]), Project.deleted_at.is_(None)
        )
    ).all():
        my_projects.append(
            {"id": p.id, "name": p.name, "status": p.status, "progress": p.progress}
        )

    my_overdue_borrows = db.scalars(
        select(EquipmentBorrow)
        .where(
            EquipmentBorrow.borrower_id == uid,
            EquipmentBorrow.status.in_((BorrowStatus.BORROWED, BorrowStatus.OVERDUE)),
            EquipmentBorrow.expected_return_time < utcnow(),
        )
        .order_by(EquipmentBorrow.expected_return_time)
        .limit(5)
    ).all()
    borrow_names = id_name_map(
        db, Equipment.id, Equipment.name, {b.equipment_id for b in my_overdue_borrows}
    )

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
            "attention": {
                "overdue_borrows": [
                    {
                        "id": b.id,
                        "equipment_name": borrow_names.get(b.equipment_id),
                        "expected_return_time": b.expected_return_time.isoformat()
                        if b.expected_return_time
                        else None,
                    }
                    for b in my_overdue_borrows
                ],
            },
            "experiments": [
                {
                    "id": e.id,
                    "experiment_no": e.experiment_no,
                    "title": e.title,
                    "status": e.status,
                    "experiment_date": e.experiment_date.isoformat()
                    if e.experiment_date
                    else None,
                }
                for e in recent_experiments
            ],
        }
    )
