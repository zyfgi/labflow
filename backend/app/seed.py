"""LabFlow seed script.

Usage (from backend/):
    python -m app.seed

Creates the demo dataset from the PRD: 1 PI, 1 teacher, 2 PhD, 5 masters,
2 undergraduates, 1 equipment admin, plus skills, projects, tasks, weekly
reports, experiments, equipment and bookings (as models allow).

Seed passwords are for DEVELOPMENT ONLY. Seeded accounts get
must_change_password=True so the frontend prompts a password change on
first login. Do not reuse these in production.
"""

import logging
import sys
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.user import MemberProfile, User

logger = logging.getLogger("labflow.seed")

DEV_PASSWORD = "Labflow@123"

# (username, name, role, member_type, research_direction, grade_year, student_no)
USERS = [
    ("admin", "张建国", "PI", "teacher", "车辆动力学与控制", None, None),
    ("teacher01", "李弘", "TEACHER", "teacher", "智能底盘控制", None, None),
    ("phd01", "王晓东", "STUDENT", "phd", "车辆参数在线估计", "2023级", "B20231001"),
    ("phd02", "刘雨欣", "STUDENT", "phd", "轮胎-路面摩擦系数估计", "2024级", "B20241002"),
    ("master01", "陈晨", "STUDENT", "master", "横摆稳定性控制", "2024级", "S20242001"),
    ("master02", "赵磊", "STUDENT", "master", "自动驾驶决策规划", "2024级", "S20242002"),
    ("master03", "孙悦", "STUDENT", "master", "多传感器融合", "2025级", "S20253003"),
    ("master04", "周涛", "STUDENT", "master", "车辆状态观测器", "2025级", "S20253004"),
    ("master05", "吴静", "STUDENT", "master", "强化学习控制", "2025级", "S20253005"),
    ("under01", "郑云", "STUDENT", "undergraduate", "数据采集与处理", "2022级", "U20221006"),
    ("under02", "冯凯", "STUDENT", "undergraduate", "实车试验", "2023级", "U20231007"),
    ("equipadmin", "徐明", "EQUIPMENT_ADMIN", "assistant", "实验室设备管理", None, None),
]


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    created = 0
    for username, name, role, member_type, direction, grade_year, student_no in USERS:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                name=name,
                role=role,
                email=f"{username}@labflow.edu.cn",
                password_hash=hash_password(DEV_PASSWORD),
                must_change_password=True,
            )
            db.add(user)
            db.flush()
            created += 1
        if user.member_profile is None:
            profile = MemberProfile(
                user_id=user.id,
                member_type=member_type,
                research_direction=direction,
                grade_year=grade_year,
                student_no=student_no,
                join_date=date(2023, 9, 1),
                status="active",
            )
            db.add(profile)
            db.flush()
        users[username] = user
    db.commit()
    logger.info("users: %d total (%d newly created)", len(users), created)
    return users


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from app.core.config import settings

    if not settings.effective_allow_demo_seed:
        logger.error(
            "Demo seed 在生产环境默认禁用（ENV=production）。"
            "如确需演示数据请显式设置 ALLOW_DEMO_SEED=true；"
            "生产管理员请使用: python -m app.cli create-admin"
        )
        sys.exit(1)

    Base.metadata.create_all(engine)  # safety net; alembic is the real path
    with SessionLocal() as db:
        users = seed_users(db)
        try:
            from app.seed_data import seed_domain  # extended per milestone

            seed_domain(db, users)
        except ImportError:
            logger.info("no extended seed data module; users only")
    logger.info("seed done. dev password for all accounts: %s", DEV_PASSWORD)


if __name__ == "__main__":
    main()
