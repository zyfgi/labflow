"""SQL query-count regression: counts must not grow with data volume.

Guards the N+1 fixes on list endpoints and the dashboard. We assert absolute
query budgets (generous, but far below per-row growth) rather than timings.
"""

import os
import tempfile
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.security import create_access_token
from app.database import Base, get_db
import app.database as dbmod
from app.models.experiment import Experiment
from app.models.project import Project, Task
from app.models.report import WeeklyReport
from app.models.user import MemberProfile, User


@pytest.fixture()
def query_env():
    tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/qc.db"
    eng = create_engine(f"sqlite:///{tmp}/qc.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, expire_on_commit=False)
    dbmod.SessionLocal = TestSession

    counter = {"n": 0}

    @event.listens_for(eng, "before_cursor_execute")
    def _count(*args, **kwargs):
        counter["n"] += 1

    def override():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    main_module.app.dependency_overrides[get_db] = override
    yield TestSession(), counter, TestClient(main_module.app)
    main_module.app.dependency_overrides.pop(get_db, None)


def _seed(s, n_tasks: int, n_projects: int = 5, n_members: int = 12):
    pi = User(username="pi", name="PI", email="pi@qc", role="PI", password_hash="x")
    s.add(pi)
    s.flush()
    students = []
    for i in range(n_members):
        u = User(username=f"s{i}", name=f"学生{i}", email=f"s{i}@qc", role="STUDENT", password_hash="x")
        s.add(u)
        s.flush()
        s.add(MemberProfile(user_id=u.id, member_type="master", status="active"))
        students.append(u)
    projects = []
    for i in range(n_projects):
        p = Project(name=f"项目{i}", code=f"QCP{i}", owner_id=pi.id, visibility="lab")
        s.add(p)
        s.flush()
        projects.append(p)
    for i in range(n_tasks):
        s.add(
            Task(
                project_id=projects[i % n_projects].id,
                title=f"任务{i}",
                assignee_id=students[i % n_members].id,
                status="todo",
                due_date=date.today() + timedelta(days=i % 10 - 3),
            )
        )
        s.add(
            Experiment(
                experiment_no=f"EXP-2026010{i % 10}-{i:04d}",
                project_id=projects[i % n_projects].id,
                title=f"实验{i}",
                owner_id=students[i % n_members].id,
                experiment_date=date.today(),
            )
        )
    for st in students:
        s.add(
            WeeklyReport(
                member_id=st.member_profile.id,
                week_start=date.today(),
                week_end=date.today(),
                status="submitted",
            )
        )
    s.commit()
    return pi, students[0]


def _headers(u: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(u.id), {'role': u.role})}"}


def _get(client, url, headers):
    import app.database as dbmod

    prev = None

    def run():
        return client.get(url, headers=headers)

    return run


@pytest.mark.parametrize("endpoint,role", [
    ("/api/v1/projects?page_size=50", "student"),
    ("/api/v1/tasks?page_size=50", "student"),
    ("/api/v1/experiments?page_size=50", "student"),
])
def test_list_query_count_stable(query_env, endpoint, role):
    s, counter, client = query_env
    pi, student = _seed(s, n_tasks=5)
    counter["n"] = 0
    client.get(endpoint, headers=_headers(student))
    small = counter["n"]

    # reset data scale (same DB keeps growing: add 45 more of each)
    from datetime import date

    projects = s.query(Project).all()
    students = s.query(User).filter(User.role == "STUDENT").all()
    for i in range(45):
        s.add(
            Task(
                project_id=projects[i % len(projects)].id,
                title=f"额外任务{i}",
                assignee_id=students[i % len(students)].id,
                status="todo",
                due_date=date.today(),
            )
        )
        s.add(
            Experiment(
                experiment_no=f"EXP-2026020{i % 10}-{i:04d}",
                project_id=projects[i % len(projects)].id,
                title=f"额外实验{i}",
                owner_id=students[i % len(students)].id,
                experiment_date=date.today(),
            )
        )
    s.commit()

    counter["n"] = 0
    r = client.get(endpoint, headers=_headers(student))
    large = counter["n"]
    assert r.status_code == 200
    assert small <= 10, f"baseline too chatty: {small}"
    # large dataset must not cost meaningfully more queries than small
    assert large <= small + 2, f"N+1 regression on {endpoint}: {small} -> {large}"


def test_dashboard_query_count_stable(query_env):
    s, counter, client = query_env
    pi, _ = _seed(s, n_tasks=5)
    counter["n"] = 0
    client.get("/api/v1/dashboard/pi", headers=_headers(pi))
    small = counter["n"]

    projects = s.query(Project).all()
    students = s.query(User).filter(User.role == "STUDENT").all()
    from datetime import date

    for i in range(45):
        s.add(
            Task(
                project_id=projects[i % len(projects)].id,
                title=f"看板任务{i}",
                assignee_id=students[i % len(students)].id,
                status="todo",
                due_date=date.today(),
            )
        )
    s.commit()

    counter["n"] = 0
    r = client.get("/api/v1/dashboard/pi", headers=_headers(pi))
    large = counter["n"]
    assert r.status_code == 200
    # fixed section budget (KPI + members + projects + todo + activity),
    # must not grow with task/member count
    assert small <= 35, f"dashboard baseline too chatty: {small}"
    assert large <= small + 3, f"dashboard N+1 regression: {small} -> {large}"
