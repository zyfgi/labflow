"""Retrieval engine tests: entity resolution, intents, permission scoping."""

from app.services.retrieval.engine import retrieve
from app.services.retrieval.intent_parser import parse_query
from tests.conftest import auth_headers


def _setup_two_projects(client, db, pi, student, student_b):
    """Project A (lab-visible, student member) + Project B (private, no student)."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": "Project Alpha", "code": "ALPHA-1", "visibility": "lab"},
        headers=auth_headers(pi),
    )
    project_a = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_a}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    resp = client.post(
        "/api/v1/projects",
        json={"name": "Project Beta", "code": "BETA-2", "visibility": "private"},
        headers=auth_headers(pi),
    )
    project_b = resp.json()["data"]["id"]
    return project_a, project_b


def test_intent_parser_rules():
    plan = parse_query("我有哪些逾期任务？")
    assert plan.intent == "overdue_tasks"
    assert plan.mine_only is True

    plan = parse_query("张三最近一个月做了什么")
    assert plan.time_preset == "last_30_days"

    plan = parse_query("六维力传感器现在什么状态")
    assert plan.intent == "equipment"

    plan = parse_query("最近有哪些 PINN 相关实验")
    assert "PINN" in [k.upper() for k in [k.upper() for k in plan.keywords]]
    assert plan.intent == "experiments"


def test_retrieval_overdue_tasks_only_mine(client, db, pi, student, student_b):
    project_a, _ = _setup_two_projects(client, db, pi, student, student_b)
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_a,
            "title": "我的逾期任务A",
            "assignee_id": student.id,
            "due_date": yesterday,
        },
        headers=auth_headers(pi),
    )
    client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_a,
            "title": "别人的逾期任务B",
            "assignee_id": student_b.id,
            "due_date": yesterday,
        },
        headers=auth_headers(pi),
    )

    plan, hits = retrieve(db, student, "我有哪些逾期任务？")
    assert plan.intent == "overdue_tasks"
    titles = [h.title for h in hits if h.source_type == "task"]
    assert any("我的逾期任务A" in t for t in titles)
    assert not any("别人的逾期任务B" in t for t in titles)


def test_retrieval_equipment_entity_and_maintenance(client, db, equip_admin, student):
    resp = client.post(
        "/api/v1/equipment",
        json={"asset_no": "FTS-100", "name": "六维力传感器", "category": "传感器"},
        headers=auth_headers(equip_admin),
    )
    equipment_id = resp.json()["data"]["id"]
    client.post(
        "/api/v1/equipment-maintenance",
        json={
            "equipment_id": equipment_id,
            "type": "fault",
            "description": "线缆断裂无输出",
        },
        headers=auth_headers(student),
    )

    plan, hits = retrieve(db, student, "六维力传感器现在什么状态？最近维修过吗？")
    assert plan.intent in ("equipment", "maintenance", "general")
    types = {h.source_type for h in hits}
    assert "equipment" in types
    assert any(
        h.source_id == equipment_id for h in hits if h.source_type == "equipment"
    )
    assert any("线缆断裂" in h.excerpt for h in hits if h.source_type == "maintenance")


def test_retrieval_experiment_no_exact(client, db, pi, student):
    project_a, _ = _setup_two_projects(
        client, db, pi, student, None or student_b_stub(client, db, pi)
    )
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_a, "title": "PINN 参数辨识实验"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    exp_no = resp.json()["data"]["experiment_no"]

    plan, hits = retrieve(db, student, f"{exp_no} 的结论是什么")
    assert any(h.source_type == "experiment" and exp_no in h.title for h in hits)


def student_b_stub(client, db, pi):
    from tests.conftest import make_user

    return make_user(db, "retrieval_stub_b", role="STUDENT", name="检索路人")


def test_retrieval_respects_time_range(client, db, pi, student):
    project_a, _ = _setup_two_projects(
        client, db, pi, student, student_b_stub(client, db, pi)
    )
    resp = client.post(
        "/api/v1/experiments",
        json={
            "project_id": project_a,
            "title": "UKF 老实验",
            "experiment_date": "2025-01-01",
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    plan, hits = retrieve(db, student, "我最近一周做了哪些实验")
    assert not any("UKF 老实验" in h.title for h in hits)


def test_member_and_learning_plan_retrieval_for_staff(client, db, pi, student):
    from tests.factories import add_project_member, create_project

    project_id = create_project(client, pi, name="成员检索项目")
    add_project_member(client, pi, project_id, student)
    from tests.conftest import make_user

    named = make_user(db, "检索员", role="STUDENT", name="检索员姓名")
    client.post(
        "/api/v1/learning-plans",
        json={"member_id": named.member_profile.id, "title": "检索计划目标"},
        headers=auth_headers(named),
    )

    plan, hits = retrieve(db, pi, "检索员姓名 最近有什么学习计划")
    types = {h.source_type for h in hits}
    assert "member" in types and "learning_plan" in types
    assert any(h.title == "检索计划目标" for h in hits if h.source_type == "learning_plan")
    assert any(h.title == "检索员姓名" for h in hits if h.source_type == "member")

    # student asking about someone else's member data: nothing leaks
    plan2, hits2 = retrieve(db, named, "检索员姓名 的学习计划")
    assert all(h.source_type != "member" for h in hits2)


def test_equipment_booking_and_own_report_paths(client, db, pi, equip_admin, student):
    from datetime import datetime, timedelta

    from tests.factories import create_booking, create_equipment

    equipment_id = create_equipment(client, equip_admin, "RT-EQ-1", name="检 Pickup设备")
    from app.core.time import app_today

    base = datetime.combine(app_today(), datetime.min.time())
    fmt = "%Y-%m-%dT%H:%M:%S"
    create_booking(client, student, equipment_id, base.strftime(fmt), (base + timedelta(hours=2)).strftime(fmt))
    client.post(
        "/api/v1/weekly-reports",
        json={"week_start": "2026-09-14", "work_summary": "采集了 Pickup 数据"},
        headers=auth_headers(student),
    )

    # equipment entity widens into equipment + booking hits
    plan, hits = retrieve(db, equip_admin, "检 Pickup设备 本周预约情况")
    assert any(h.source_type == "equipment" for h in hits)
    assert any(h.source_type == "booking" for h in hits)

    # student's own report question: person-scoped, no keyword dependence
    plan2, hits2 = retrieve(db, student, "我最近的周报写了什么")
    assert any(h.source_type == "weekly_report" and "Pickup" in (h.metadata.get("context", {}).get("work_summary") or "") for h in hits2)
