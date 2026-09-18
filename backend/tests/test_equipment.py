"""Equipment light-process tests.

Contract (manual §49-§51): booking succeeds immediately when conflict-free
(reserved), conflict is the only hard block (409), cancel acts at once,
approve/reject endpoints no longer exist; borrow/return/extend act at once
and notify equipment watchers; a fault report takes effect immediately.
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.system import AuditLog, Notification
from tests.conftest import auth_headers
from tests.factories import create_booking


def make_equipment(client, equip_admin, asset_no="AST-001", status="available") -> int:
    resp = client.post(
        "/api/v1/equipment",
        json={
            "asset_no": asset_no,
            "name": "六维力传感器",
            "category": "传感器",
            "status": status,
        },
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def future(hours_ahead: int, base: datetime | None = None) -> datetime:
    base = base or datetime(2026, 9, 20, 10, 0, 0)
    return base + timedelta(hours=hours_ahead)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def test_student_cannot_create_or_modify_equipment(client, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin)
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": "STU-1", "name": "X", "category": "Y"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403
    resp = client.patch(
        f"/api/v1/equipment/{equipment_id}",
        json={"name": "hacked"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403


def test_booking_immediate_reserved_with_notification_and_audit(
    client, db, pi, equip_admin, student
):
    equipment_id = make_equipment(client, equip_admin)
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(future(0)),
            "end_time": iso(future(2)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    booking_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["status"] == "reserved"

    # watchers (equipment admin) hear about it; the booker does not self-notify
    notes = db.scalars(
        select(Notification).where(Notification.type == "equipment_booked")
    ).all()
    assert {n.user_id for n in notes} == {equip_admin.id}

    assert (
        db.scalar(
            select(AuditLog).where(
                AuditLog.action == "create_booking",
                AuditLog.resource_id == str(booking_id),
            )
        )
        is not None
    )


def test_booking_conflict_is_the_only_hard_block(client, equip_admin, student):
    """reserved A 10:00-12:00; overlapping B -> 409, no approval step involved."""
    equipment_id = make_equipment(client, equip_admin)
    base = datetime(2026, 9, 20, 10, 0, 0)
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(base),
            "end_time": iso(base + timedelta(hours=2)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "reserved"

    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(base + timedelta(hours=1)),
            "end_time": iso(base + timedelta(hours=3)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 409


def test_adjacent_bookings_allowed(client, equip_admin, student):
    """end == start (back-to-back) must NOT count as overlap."""
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-ADJ")
    base = datetime(2026, 9, 22, 8, 0, 0)
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(base),
            "end_time": iso(base + timedelta(hours=1)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(base + timedelta(hours=1)),
            "end_time": iso(base + timedelta(hours=2)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201


def test_cancel_immediate_with_notification(client, db, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-CXL")
    booking_id = create_booking(
        client, student, equipment_id, iso(future(0)), iso(future(2))
    )

    resp = client.post(
        f"/api/v1/equipment-bookings/{booking_id}/cancel", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"

    notes = db.scalars(
        select(Notification).where(Notification.type == "equipment_booking_cancelled")
    ).all()
    assert {n.user_id for n in notes} == {equip_admin.id}

    # cancelled is terminal
    resp = client.post(
        f"/api/v1/equipment-bookings/{booking_id}/cancel", headers=auth_headers(student)
    )
    assert resp.status_code == 400


def test_no_approve_or_reject_endpoints(client, pi, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-GONE")
    booking_id = create_booking(
        client, student, equipment_id, iso(future(0)), iso(future(2))
    )
    for action in ("approve", "reject"):
        resp = client.post(
            f"/api/v1/equipment-bookings/{booking_id}/{action}",
            headers=auth_headers(equip_admin),
        )
        assert resp.status_code in (404, 405), f"{action} should not exist"


def test_borrow_return_extend_with_notifications(client, db, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-BORROW")
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": equipment_id, "expected_return_time": iso(future(24))},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201, resp.text
    borrow_id = resp.json()["data"]["id"]
    assert (
        db.scalar(select(Notification).where(Notification.type == "equipment_borrowed"))
        is not None
    )

    resp = client.get(
        f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student)
    )
    assert resp.json()["data"]["status"] == "borrowed"

    # cannot borrow twice while out
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": equipment_id, "expected_return_time": iso(future(25))},
        headers=auth_headers(student),
    )
    assert resp.status_code == 409

    # extension: push the return time out, no approval needed
    resp = client.patch(
        f"/api/v1/equipment-borrows/{borrow_id}",
        json={"expected_return_time": iso(future(48))},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["expected_return_time"].startswith("2026-09-22")
    assert (
        db.scalar(select(AuditLog).where(AuditLog.action == "extend_borrow"))
        is not None
    )

    # an extension target in the past is rejected (server clock is UTC)
    from app.core.time import utcnow as _utcnow

    resp = client.patch(
        f"/api/v1/equipment-borrows/{borrow_id}",
        json={
            "expected_return_time": (_utcnow() - timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 422

    # return
    resp = client.post(
        f"/api/v1/equipment-borrows/{borrow_id}/return", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "returned"
    assert (
        db.scalar(select(Notification).where(Notification.type == "equipment_returned"))
        is not None
    )
    resp = client.get(
        f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student)
    )
    assert resp.json()["data"]["status"] == "available"


def test_fault_report_immediate_and_notifies_watchers_and_bookers(
    client, db, equip_admin, student
):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-FAULT")
    # a student holds a future reservation on this equipment
    booking_student = student
    create_booking(
        client, booking_student, equipment_id, iso(future(0)), iso(future(2))
    )

    resp = client.post(
        "/api/v1/equipment-maintenance",
        json={
            "equipment_id": equipment_id,
            "type": "fault",
            "description": "传感器无输出",
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    record_id = resp.json()["data"]["id"]

    # the fault takes effect before any admin confirmation
    resp = client.get(
        f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student)
    )
    assert resp.json()["data"]["status"] == "fault"

    notes = db.scalars(
        select(Notification).where(Notification.type == "equipment_fault")
    ).all()
    # reporter excluded; equipment admin + affected booker notified
    assert notes and all(n.user_id != student.id for n in notes)
    assert {n.user_id for n in notes} == {equip_admin.id, booking_student.id} - {
        student.id
    }

    # student cannot process maintenance
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "processing"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403

    # admin processes -> equipment in maintenance, then completed -> available
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "processing", "vendor": "厂家售后"},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 200
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "completed", "result": "更换接口板", "cost": "800"},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 200
    resp = client.get(
        f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student)
    )
    assert resp.json()["data"]["status"] == "available"
    # the reporter hears the maintenance progress
    assert (
        db.scalar(
            select(Notification).where(Notification.type == "maintenance_updated")
        )
        is not None
    )


def test_booking_invalid_time_range(client, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-TIME")
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(future(6)),
            "end_time": iso(future(4)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 422


def test_faulted_equipment_cannot_be_booked(client, equip_admin, student):
    equipment_id = make_equipment(
        client, equip_admin, asset_no="AST-FBK", status="fault"
    )
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(future(0)),
            "end_time": iso(future(2)),
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 400


def test_equipment_admin_lists_others_bookings_and_borrows(
    client, equip_admin, student
):
    equipment_id = make_equipment(client, equip_admin, asset_no="VIS-EQ-1")
    base = datetime(2026, 10, 1, 9, 0, 0)
    booking_id = create_booking(
        client,
        student,
        equipment_id,
        base.strftime("%Y-%m-%dT%H:%M:%S"),
        (base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={
            "equipment_id": equipment_id,
            "expected_return_time": (base + timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
        },
        headers=auth_headers(student),
    )
    borrow_id = resp.json()["data"]["id"]

    admin_seen = client.get(
        "/api/v1/equipment-bookings", headers=auth_headers(equip_admin)
    ).json()["data"]
    assert any(b["id"] == booking_id for b in admin_seen["items"])
    admin_borrows = client.get(
        "/api/v1/equipment-borrows", headers=auth_headers(equip_admin)
    ).json()["data"]
    assert any(b["id"] == borrow_id for b in admin_borrows["items"])


def test_student_only_lists_own_bookings(client, equip_admin, student, student_b):
    equipment_id = make_equipment(client, equip_admin, asset_no="VIS-EQ-2")
    base = datetime(2026, 10, 2, 9, 0, 0)
    fmt = "%Y-%m-%dT%H:%M:%S"
    own_booking = create_booking(
        client,
        student,
        equipment_id,
        base.strftime(fmt),
        (base + timedelta(hours=1)).strftime(fmt),
    )
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": (base + timedelta(hours=3)).strftime(fmt),
            "end_time": (base + timedelta(hours=4)).strftime(fmt),
        },
        headers=auth_headers(student_b),
    )
    other_booking = resp.json()["data"]["id"]

    seen = client.get(
        "/api/v1/equipment-bookings", headers=auth_headers(student)
    ).json()["data"]
    ids = {b["id"] for b in seen["items"]}
    assert own_booking in ids
    assert other_booking not in ids


def test_past_expected_return_time_rejected(client, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="VIS-EQ-3")
    past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": equipment_id, "expected_return_time": past},
        headers=auth_headers(student),
    )
    assert resp.status_code == 422


def test_invalid_maintenance_transition_denied(client, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="VIS-EQ-4")
    resp = client.post(
        "/api/v1/equipment-maintenance",
        json={"equipment_id": equipment_id, "type": "fault", "description": "x"},
        headers=auth_headers(student),
    )
    record_id = resp.json()["data"]["id"]
    # reported -> completed is not a legal transition
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "completed"},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 400
    # terminal states cannot resume
    client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "cancelled"},
        headers=auth_headers(equip_admin),
    )
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}",
        json={"status": "processing"},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 400


def test_qr_generate_resolve_and_rotate(client, db, equip_admin, student):
    from app.services import runtime_settings

    equipment_id = make_equipment(client, equip_admin, asset_no="AST-QR")

    # student cannot generate
    resp = client.post(
        f"/api/v1/equipment/{equipment_id}/qr", headers=auth_headers(student)
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/api/v1/equipment/{equipment_id}/qr", headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 201
    token = resp.json()["data"]["qr_token"]
    assert token

    # resolve works for any authenticated member (QR is a pointer, not a credential)
    resp = client.get(f"/api/v1/qr/{token}", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["data"]["equipment_id"] == equipment_id

    # regenerating invalidates the old tag
    resp = client.post(
        f"/api/v1/equipment/{equipment_id}/qr?regenerate=true",
        headers=auth_headers(equip_admin),
    )
    new_token = resp.json()["data"]["qr_token"]
    assert new_token != token
    resp = client.get(f"/api/v1/qr/{token}", headers=auth_headers(student))
    assert resp.status_code == 404
    assert (
        db.scalar(
            select(AuditLog).where(
                AuditLog.action == "regenerate_qr",
                AuditLog.resource_id == str(equipment_id),
            )
        )
        is not None
    )

    # PUBLIC_BASE_URL drives the printable URL
    runtime_settings.update_runtime(
        db,
        runtime_settings.RuntimeSettingsUpdate(
            PUBLIC_BASE_URL="https://lab.example.edu"
        ),
        updated_by=equip_admin.id,
    )
    item = client.get(
        f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student)
    ).json()["data"]
    assert item["qr_url"] == f"https://lab.example.edu/q/{item['qr_token']}"
