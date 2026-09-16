"""Equipment tests: ledger permissions, booking conflict, borrow/return, fault (PRD §29/§45 Phase G)."""

from datetime import datetime, timedelta

from tests.conftest import auth_headers


def make_equipment(client, equip_admin, asset_no="AST-001", status="available") -> int:
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": asset_no, "name": "六维力传感器", "category": "传感器", "status": status},
        headers=auth_headers(equip_admin),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def future(hours_ahead: int, base: datetime | None = None) -> datetime:
    base = base or datetime(2026, 9, 20, 10, 0, 0)
    return base + timedelta(hours=hours_ahead)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def test_student_cannot_create_or_modify_equipment(client, db, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin)
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": "STU-1", "name": "X", "category": "Y"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403
    resp = client.patch(
        f"/api/v1/equipment/{equipment_id}", json={"name": "hacked"}, headers=auth_headers(student)
    )
    assert resp.status_code == 403


def test_booking_conflict_rejected(client, db, pi, equip_admin, student):
    """booking A 10:00-12:00 approved; booking B 11:00-13:00 must fail (PRD Phase G)."""
    equipment_id = make_equipment(client, equip_admin)
    base = datetime(2026, 9, 20, 10, 0, 0)
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={"equipment_id": equipment_id, "start_time": iso(base), "end_time": iso(base + timedelta(hours=2))},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    booking_a = resp.json()["data"]["id"]

    resp = client.post(
        f"/api/v1/equipment-bookings/{booking_a}/approve", headers=auth_headers(equip_admin)
    )
    assert resp.status_code == 200

    # B overlaps with approved A -> 409
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


def test_adjacent_bookings_allowed(client, db, equip_admin, student):
    """end == start (back-to-back) must NOT count as overlap."""
    equipment_id = make_equipment(client, equip_admin)
    base = datetime(2026, 9, 22, 8, 0, 0)
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={"equipment_id": equipment_id, "start_time": iso(base), "end_time": iso(base + timedelta(hours=1))},
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


def test_approve_reject_and_notification(client, db, pi, equip_admin, student):
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
    booking_id = resp.json()["data"]["id"]

    # student cannot approve
    resp = client.post(f"/api/v1/equipment-bookings/{booking_id}/approve", headers=auth_headers(student))
    assert resp.status_code == 403

    # admin approves -> notification for student
    resp = client.post(f"/api/v1/equipment-bookings/{booking_id}/approve", headers=auth_headers(equip_admin))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "approved"

    from sqlalchemy import select

    from app.models.system import Notification

    notes = db.scalars(select(Notification).where(Notification.user_id == student.id)).all()
    assert any(n.type == "booking_approved" for n in notes)

    # second booking then reject
    resp = client.post(
        "/api/v1/equipment-bookings",
        json={
            "equipment_id": equipment_id,
            "start_time": iso(future(4)),
            "end_time": iso(future(6)),
        },
        headers=auth_headers(student),
    )
    booking2 = resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/equipment-bookings/{booking2}/reject", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"


def test_borrow_return_flow_and_status(client, db, pi, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-BORROW")
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": equipment_id, "expected_return_time": iso(future(24))},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201, resp.text
    borrow_id = resp.json()["data"]["id"]

    resp = client.get(f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student))
    assert resp.json()["data"]["status"] == "borrowed"

    # cannot borrow twice
    resp = client.post(
        "/api/v1/equipment-borrows",
        json={"equipment_id": equipment_id, "expected_return_time": iso(future(25))},
        headers=auth_headers(pi),
    )
    assert resp.status_code == 409

    # return
    resp = client.post(f"/api/v1/equipment-borrows/{borrow_id}/return", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "returned"
    resp = client.get(f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student))
    assert resp.json()["data"]["status"] == "available"


def test_fault_report_changes_status_and_admin_process(client, db, pi, equip_admin, student):
    equipment_id = make_equipment(client, equip_admin, asset_no="AST-FAULT")
    resp = client.post(
        "/api/v1/equipment-maintenance",
        json={"equipment_id": equipment_id, "type": "fault", "description": "传感器无输出"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    record_id = resp.json()["data"]["id"]

    resp = client.get(f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student))
    assert resp.json()["data"]["status"] == "fault"

    # student cannot process maintenance
    resp = client.patch(
        f"/api/v1/equipment-maintenance/{record_id}", json={"status": "processing"}, headers=auth_headers(student)
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
    resp = client.get(f"/api/v1/equipment/{equipment_id}", headers=auth_headers(student))
    assert resp.json()["data"]["status"] == "available"


def test_booking_invalid_time_range(client, db, equip_admin, student):
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
