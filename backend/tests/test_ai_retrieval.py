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
        json={"project_id": project_a, "title": "我的逾期任务A", "assignee_id": student.id, "due_date": yesterday},
        headers=auth_headers(pi),
    )
    client.post(
        "/api/v1/tasks",
        json={"project_id": project_a, "title": "别人的逾期任务B", "assignee_id": student_b.id, "due_date": yesterday},
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
        json={"equipment_id": equipment_id, "type": "fault", "description": "线缆断裂无输出"},
        headers=auth_headers(student),
    )

    plan, hits = retrieve(db, student, "六维力传感器现在什么状态？最近维修过吗？")
    assert plan.intent in ("equipment", "maintenance", "general")
    types = {h.source_type for h in hits}
    assert "equipment" in types
    assert any(h.source_id == equipment_id for h in hits if h.source_type == "equipment")
    assert any("线缆断裂" in h.excerpt for h in hits if h.source_type == "maintenance")


def test_retrieval_experiment_no_exact(client, db, pi, student):
    project_a, _ = _setup_two_projects(client, db, pi, student, None or student_b_stub(client, db, pi))
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
    project_a, _ = _setup_two_projects(client, db, pi, student, student_b_stub(client, db, pi))
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_a, "title": "UKF 老实验", "experiment_date": "2025-01-01"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201
    plan, hits = retrieve(db, student, "我最近一周做了哪些实验")
    assert not any("UKF 老实验" in h.title for h in hits)
