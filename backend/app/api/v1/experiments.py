from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, write_audit_log
from app.core.responses import ok, paged
from app.core.time import app_today, utcnow
from app.database import get_db
from app.models.experiment import Experiment, ExperimentAttachment
from app.models.project import Project
from app.models.user import User
from app.permissions.projects import (
    can_create_experiment,
    can_manage_project,
    can_read_project,
    visible_project_ids_subquery,
)
from app.schemas.experiment import ExperimentCreate, ExperimentOut, ExperimentUpdate
from app.storage import storage_service

router = APIRouter(prefix="/experiments", tags=["experiments"])
attachments_router = APIRouter(prefix="/experiment-attachments", tags=["experiments"])


def _get_experiment(db: Session, experiment_id: int) -> Experiment:
    exp = db.get(Experiment, experiment_id)
    if not exp or exp.deleted_at is not None:
        raise HTTPException(status_code=404, detail="实验记录不存在")
    return exp


def _ensure_experiment_visible(db: Session, user: User, exp: Experiment) -> None:
    project = db.get(Project, exp.project_id)
    if not project or not can_read_project(db, user, project):
        raise HTTPException(status_code=403, detail="没有查看该实验的权限")


def _can_edit_experiment(db: Session, user: User, exp: Experiment) -> bool:
    # a locked record is frozen for everyone, including PI — unlock first
    if exp.is_locked:
        return False
    project = db.get(Project, exp.project_id)
    if exp.owner_id == user.id:
        return True
    return bool(project and can_manage_project(db, user, project))


def _can_lock(db: Session, user: User, exp: Experiment) -> bool:
    project = db.get(Project, exp.project_id)
    return bool(project and can_manage_project(db, user, project))


def _out(exp: Experiment, db: Session | None = None, with_owner: bool = False) -> dict:
    data = ExperimentOut.model_validate(exp).model_dump()
    if with_owner and db is not None and exp.owner_id:
        from app.models.user import User

        owner = db.get(User, exp.owner_id)
        data["owner_name"] = owner.name if owner else None
    return data


def _generate_experiment_no(db: Session) -> str:
    prefix = f"EXP-{app_today().strftime('%Y%m%d')}-"
    count = (
        db.scalar(
            select(func.count())
            .select_from(Experiment)
            .where(Experiment.experiment_no.like(f"{prefix}%"))
        )
        or 0
    )
    for attempt in range(50):
        candidate = f"{prefix}{count + attempt + 1:04d}"
        exists = db.scalar(
            select(Experiment.id).where(Experiment.experiment_no == candidate)
        )
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="实验编号生成失败，请重试")


@router.get("")
def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: int | None = None,
    owner_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Experiment).where(Experiment.deleted_at.is_(None))
    if mine:
        owner_id = user.id
    if owner_id:
        stmt = stmt.where(Experiment.owner_id == owner_id)

    if project_id:
        project = db.get(Project, project_id)
        if not project or not can_read_project(db, user, project):
            raise HTTPException(status_code=403, detail="没有查看该项目的权限")
        stmt = stmt.where(Experiment.project_id == project_id)
    else:
        # shared permission scope, pushed into SQL
        stmt = stmt.where(Experiment.project_id.in_(visible_project_ids_subquery(user)))

    if status:
        stmt = stmt.where(Experiment.status == status)
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(
            Experiment.title.ilike(kw) | Experiment.experiment_no.ilike(kw)
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Experiment.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # batch maps: constant query count regardless of page size
    owner_ids = {e.owner_id for e in rows if e.owner_id}
    owner_names = dict(
        db.execute(
            select(User.id, User.name).where(User.id.in_(owner_ids or [0]))
        ).all()
    )
    project_names = dict(
        db.execute(
            select(Project.id, Project.name).where(
                Project.id.in_({e.project_id for e in rows} or [0])
            )
        ).all()
    )

    items = []
    for exp in rows:
        item = _out(exp)
        item["owner_name"] = owner_names.get(exp.owner_id)
        item["project_name"] = project_names.get(exp.project_id)
        items.append(item)
    return paged(items, total, page, page_size)


@router.post("", status_code=201)
def create_experiment(
    body: ExperimentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = db.get(Project, body.project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="项目不存在")
    # lab visibility alone is NOT enough: creating records requires membership
    if not can_create_experiment(db, user, project):
        raise HTTPException(status_code=403, detail="只有项目成员可以创建实验记录")

    exp = Experiment(
        **body.model_dump(exclude={"experiment_date"}),
        experiment_no=_generate_experiment_no(db),
        owner_id=user.id,
        status="draft",
        experiment_date=body.experiment_date or app_today(),
    )
    db.add(exp)
    db.flush()
    write_audit_log(
        db, user, "create_experiment", "experiment", exp.id, {"no": exp.experiment_no}
    )
    db.commit()
    return ok(_out(exp), message="实验记录已创建")


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    _ensure_experiment_visible(db, user, exp)
    item = _out(exp, db, with_owner=True)
    proj = db.get(Project, exp.project_id)
    item["project_name"] = proj.name if proj else None
    item["can_edit"] = _can_edit_experiment(db, user, exp)
    item["can_lock"] = _can_lock(db, user, exp)
    attachments = db.scalars(
        select(ExperimentAttachment).where(ExperimentAttachment.experiment_id == exp.id)
    ).all()
    item["attachments"] = [
        {
            "id": a.id,
            "file_name": a.file_name,
            "file_type": a.file_type,
            "file_size": a.file_size,
            "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
        }
        for a in attachments
    ]
    return ok(item)


@router.patch("/{experiment_id}")
def update_experiment(
    experiment_id: int,
    body: ExperimentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    if not _can_edit_experiment(db, user, exp):
        if exp.is_locked:
            raise HTTPException(status_code=403, detail="实验已锁定，不能修改")
        raise HTTPException(status_code=403, detail="只有实验负责人可以修改")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(exp, field, value)
    write_audit_log(
        db,
        user,
        "update_experiment",
        "experiment",
        exp.id,
        {"fields": list(data.keys())},
    )
    db.commit()
    return ok(_out(exp), message="实验已更新")


@router.delete("/{experiment_id}")
def delete_experiment(
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    if exp.is_locked:
        raise HTTPException(status_code=403, detail="实验已锁定，不能删除")
    if not _can_lock(db, user, exp):
        raise HTTPException(status_code=403, detail="只有项目管理方可以删除实验")
    exp.deleted_at = utcnow()
    write_audit_log(db, user, "delete_experiment", "experiment", exp.id)
    db.commit()
    return ok(message="实验已删除")


@router.post("/{experiment_id}/lock")
def lock_experiment(
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    if not _can_lock(db, user, exp):
        raise HTTPException(status_code=403, detail="只有 PI/项目负责人可以锁定实验")
    if exp.is_locked:
        raise HTTPException(status_code=400, detail="实验已锁定")
    exp.is_locked = True
    exp.locked_at = utcnow()
    exp.locked_by = user.id
    write_audit_log(
        db, user, "lock_experiment", "experiment", exp.id, {"no": exp.experiment_no}
    )
    db.commit()
    return ok(_out(exp), message="实验已锁定")


@router.post("/{experiment_id}/unlock")
def unlock_experiment(
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    if not _can_lock(db, user, exp):
        raise HTTPException(status_code=403, detail="只有 PI/项目负责人可以解锁实验")
    if not exp.is_locked:
        raise HTTPException(status_code=400, detail="实验未锁定")
    exp.is_locked = False
    exp.locked_at = None
    exp.locked_by = None
    write_audit_log(
        db, user, "unlock_experiment", "experiment", exp.id, {"no": exp.experiment_no}
    )
    db.commit()
    return ok(_out(exp), message="实验已解锁")


# ---------- attachments ----------


@router.post("/{experiment_id}/attachments", status_code=201)
def upload_attachment(
    experiment_id: int,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    exp = _get_experiment(db, experiment_id)
    if not _can_edit_experiment(db, user, exp):
        raise HTTPException(status_code=403, detail="没有上传权限（实验可能已锁定）")
    from app.services import runtime_settings

    cfg = runtime_settings.effective(db)
    rel_path, size, content_type = storage_service.save_upload(
        f"experiments/{exp.id}",
        file,
        max_bytes=cfg.UPLOAD_MAX_MB * 1024 * 1024,
        allowed_extensions=cfg.ALLOWED_UPLOAD_EXTENSIONS,
    )
    att = ExperimentAttachment(
        experiment_id=exp.id,
        file_name=file.filename or "file",
        file_type=content_type.split("/")[-1][:50],
        file_size=size,
        storage_path=rel_path,
        uploaded_by=user.id,
    )
    db.add(att)
    write_audit_log(
        db, user, "upload_attachment", "experiment", exp.id, {"file": att.file_name}
    )
    db.commit()
    return ok(
        {
            "id": att.id,
            "file_name": att.file_name,
            "file_size": att.file_size,
            "file_type": att.file_type,
        },
        message="附件上传成功",
    )


@attachments_router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    att = db.get(ExperimentAttachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    exp = _get_experiment(db, att.experiment_id)
    # a locked experiment is frozen: the uploader cannot delete via uploaded_by
    if not (
        _can_edit_experiment(db, user, exp)
        or (not exp.is_locked and att.uploaded_by == user.id)
    ):
        raise HTTPException(status_code=403, detail="没有删除该附件的权限")
    storage_service.delete(att.storage_path)
    db.delete(att)
    write_audit_log(
        db, user, "delete_attachment", "experiment", exp.id, {"file": att.file_name}
    )
    db.commit()
    return ok(message="附件已删除")


@attachments_router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    att = db.get(ExperimentAttachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    exp = _get_experiment(db, att.experiment_id)
    _ensure_experiment_visible(db, user, exp)
    path = storage_service.open_path(att.storage_path)
    return FileResponse(
        path, filename=att.file_name, media_type="application/octet-stream"
    )
