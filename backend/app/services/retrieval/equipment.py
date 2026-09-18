"""Equipment / maintenance / booking retrieval (visible to lab members)."""

from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.time import app_today, time_range
from app.models.equipment import Equipment, EquipmentBooking, EquipmentMaintenance
from app.models.user import User
from app.services.lookups import id_name_map
from app.services.retrieval.common import truncate
from app.services.retrieval.entity_resolver import ResolvedEntities
from app.services.retrieval.types import RetrievalHit, RetrievalPlan


def search_equipment(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = select(Equipment).where(Equipment.deleted_at.is_(None))
    if entities.equipment:
        stmt = stmt.where(Equipment.id == entities.equipment.id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.found:
        fields = (
            Equipment.name,
            Equipment.asset_no,
            Equipment.model,
            Equipment.category,
            Equipment.location,
        )
        stmt = stmt.where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in fields)) for kw in keywords))
        )

    rows = db.scalars(stmt.limit(limit * 2)).all()
    manager_names = id_name_map(db, User.id, User.name, {e.manager_id for e in rows})
    hits: list[RetrievalHit] = []
    today = app_today()
    for e in rows:
        score = 1.0
        for kw in keywords:
            if (
                kw.lower() in (e.name or "").lower()
                or kw.lower() in (e.asset_no or "").lower()
            ):
                score += 5
            if e.model and kw.lower() in e.model.lower():
                score += 2
        if entities.equipment and e.id == entities.equipment.id:
            score += 5
        manager_name = manager_names.get(e.manager_id)
        hits.append(
            RetrievalHit(
                source_type="equipment",
                source_id=e.id,
                title=f"{e.name} ({e.asset_no})",
                excerpt=truncate(
                    f"状态 {e.status} · 位置 {e.location or '未知'} · 型号 {e.model or '-'}"
                ),
                score=score,
                url=f"/equipment/{e.id}",
                project_id=None,
                occurred_at=None,
                metadata={
                    "status": e.status,
                    "category": e.category,
                    "location": e.location,
                    "manager_name": manager_name,
                    "model": e.model,
                    "as_of": today.isoformat(),
                    "context": {
                        "asset_no": e.asset_no,
                        "name": e.name,
                        "category": e.category,
                        "model": e.model,
                        "location": e.location,
                        "status": e.status,
                        "manager_name": manager_name,
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def search_maintenance(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    stmt = (
        select(EquipmentMaintenance)
        .join(Equipment, EquipmentMaintenance.equipment_id == Equipment.id)
        .where(Equipment.deleted_at.is_(None))
    )
    if entities.equipment:
        stmt = stmt.where(EquipmentMaintenance.equipment_id == entities.equipment.id)

    keywords = [k for k in plan.keywords if k]
    if keywords and use_keywords and not entities.equipment:
        fields = (
            EquipmentMaintenance.description,
            EquipmentMaintenance.result,
            EquipmentMaintenance.vendor,
        )
        stmt = stmt.where(
            or_(*(or_(*(f.ilike(f"%{kw}%") for f in fields)) for kw in keywords))
        )

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(EquipmentMaintenance.reported_at >= date_from)
    if date_to:
        # reported_at is a timestamp; an inclusive day bound must extend to midnight
        stmt = stmt.where(
            EquipmentMaintenance.reported_at < date_to + timedelta(days=1)
        )

    rows = db.scalars(
        stmt.order_by(EquipmentMaintenance.reported_at.desc()).limit(limit * 2)
    ).all()
    equipment_map = id_name_map(
        db, Equipment.id, Equipment.name, {m.equipment_id for m in rows}
    )
    hits: list[RetrievalHit] = []
    for m in rows:
        eq_name = equipment_map.get(m.equipment_id)
        score = 2.0
        for kw in keywords:
            if m.description and kw.lower() in m.description.lower():
                score += 3
            if m.result and kw.lower() in m.result.lower():
                score += 3
        if entities.equipment and m.equipment_id == entities.equipment.id:
            score += 4
        hits.append(
            RetrievalHit(
                source_type="maintenance",
                source_id=m.id,
                title=f"维修记录：{eq_name or m.equipment_id}（{m.type}）",
                excerpt=truncate(
                    f"状态 {m.status} · {m.description or ''} {m.result or ''}"
                ),
                score=score,
                url=f"/equipment/{m.equipment_id}",
                project_id=None,
                occurred_at=m.reported_at,
                metadata={
                    "equipment_name": eq_name,
                    "maintenance_status": m.status,
                    "vendor": m.vendor,
                    "result": truncate(m.result, 120) or None,
                    "context": {
                        "equipment_name": eq_name,
                        "type": m.type,
                        "description": truncate(m.description, 400),
                        "status": m.status,
                        "reported_at": m.reported_at.isoformat()
                        if m.reported_at
                        else None,
                        "finished_at": m.finished_at.isoformat()
                        if m.finished_at
                        else None,
                        "result": truncate(m.result, 300),
                    },
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def search_bookings(
    db: Session,
    user: User,
    plan: RetrievalPlan,
    entities: ResolvedEntities,
    limit: int = 5,
    use_keywords: bool = True,
) -> list[RetrievalHit]:
    """Booking visibility: staff/equipment-admin see all; others see only own."""
    from app.permissions import TEACHING_STAFF_ROLES

    stmt = (
        select(EquipmentBooking)
        .join(Equipment, EquipmentBooking.equipment_id == Equipment.id)
        .where(Equipment.deleted_at.is_(None))
        .options(joinedload(EquipmentBooking.user))
    )
    if user.role not in TEACHING_STAFF_ROLES and user.role != "EQUIPMENT_ADMIN":
        stmt = stmt.where(EquipmentBooking.user_id == user.id)
    if plan.mine_only:
        stmt = stmt.where(EquipmentBooking.user_id == user.id)
    if entities.equipment:
        stmt = stmt.where(EquipmentBooking.equipment_id == entities.equipment.id)

    date_from, date_to = time_range(plan.time_preset)
    if date_from:
        stmt = stmt.where(EquipmentBooking.start_time >= date_from)
    if date_to:
        stmt = stmt.where(EquipmentBooking.start_time < date_to + timedelta(days=1))

    rows = db.scalars(
        stmt.order_by(EquipmentBooking.start_time.desc()).limit(limit * 2)
    ).all()
    equipment_map = id_name_map(
        db, Equipment.id, Equipment.name, {b.equipment_id for b in rows}
    )
    hits: list[RetrievalHit] = []
    for b in rows:
        eq_name = equipment_map.get(b.equipment_id)
        score = 2.0
        if entities.equipment and b.equipment_id == entities.equipment.id:
            score += 4
        hits.append(
            RetrievalHit(
                source_type="booking",
                source_id=b.id,
                title=f"预约：{eq_name or b.equipment_id}",
                excerpt=truncate(
                    f"{b.start_time.strftime('%m-%d %H:%M')} ~ {b.end_time.strftime('%m-%d %H:%M')} · "
                    f"{b.user.name if b.user else ''} · {b.purpose or ''} · {b.status}"
                ),
                score=score,
                url="/equipment-bookings",
                project_id=b.project_id,
                occurred_at=b.start_time,
                metadata={
                    "booking_status": b.status,
                    "equipment_name": eq_name,
                    "user_name": b.user.name if b.user else None,
                },
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
