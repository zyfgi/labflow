"""Pytest fixtures.

Tests run on a file-based SQLite database (fast, no external service);
the production stack runs on PostgreSQL via Alembic. DATABASE_URL is set
before app imports so app.core.config picks it up.
"""

import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_tmpdir = tempfile.mkdtemp(prefix="labflow_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["UPLOAD_DIR"] = os.path.join(_tmpdir, "storage")
os.environ["LABFLOW_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["AI_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["AI_RATE_LIMIT_PER_DAY"] = "10000"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import Base, SessionLocal, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import MemberProfile, User  # noqa: E402


@pytest.fixture()
def db() -> Iterator[Session]:
    Base.metadata.create_all(SessionLocal.kw["bind"])
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(SessionLocal.kw["bind"])


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        try:
            yield db
        finally:
            db.rollback()  # discard any uncommitted test leftovers

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(
    db: Session,
    username: str,
    role: str = "STUDENT",
    name: str | None = None,
    password: str = "pass123456",
    member_type: str = "master",
) -> User:
    user = User(
        username=username,
        name=name or username,
        email=f"{username}@test.local",
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()
    db.add(MemberProfile(user_id=user.id, member_type=member_type, status="active"))
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id), {"role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pi(db: Session) -> User:
    return make_user(db, "pi_test", role="PI", name="张PI", member_type="teacher")


@pytest.fixture()
def teacher(db: Session) -> User:
    return make_user(db, "teacher_test", role="TEACHER", name="李老师", member_type="teacher")


@pytest.fixture()
def student(db: Session) -> User:
    return make_user(db, "student_test", role="STUDENT", name="陈同学")


@pytest.fixture()
def student_b(db: Session) -> User:
    return make_user(db, "student_b_test", role="STUDENT", name="赵同学")


@pytest.fixture()
def equip_admin(db: Session) -> User:
    return make_user(db, "equipadmin_test", role="EQUIPMENT_ADMIN", name="徐管理", member_type="assistant")
