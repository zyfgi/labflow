"""Extended seed data: skills, member skills, learning plans, projects,
tasks, weekly reports, experiments, equipment, bookings.

Called from app.seed.seed_users -> seed_domain(db, users).
Deterministic (no randomness) so repeated runs produce the same dataset.
Idempotent: every insert checks for existing rows first.
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password  # noqa: F401 (import parity for callers)
from app.models.enums import (
    ExperimentStatus,
    PlanStatus,
    ProjectStatus,
    ReportStatus,
    TaskStatus,
)
from app.models.experiment import Experiment
from app.models.learning import LearningPlan, MemberSkill, Skill
from app.models.project import Milestone, Project, ProjectMember, Task
from app.models.report import WeeklyReport
from app.models.user import MemberProfile

logger = logging.getLogger("labflow.seed")

SKILLS = [
    ("Python", "编程语言", "数据处理与建模脚本", 1),
    ("PyTorch", "深度学习", "模型训练与部署", 2),
    ("MATLAB", "仿真工具", "数值仿真", 3),
    ("Simulink", "仿真工具", "控制策略建模", 4),
    ("CarSim", "车辆仿真", "整车动力学仿真", 5),
    ("车辆动力学", "领域知识", "建模与参数估计", 6),
    ("控制理论", "领域知识", "状态估计与控制综合", 7),
    ("数据处理", "工程能力", "采集/清洗/对齐", 8),
    ("论文写作", "科研能力", "学术写作与投稿", 9),
    ("实车实验", "实验能力", "台架与实车试验", 10),
]

# skill name -> {username: level}
MEMBER_SKILLS = {
    "Python": {"admin": 4, "teacher01": 4, "phd01": 4, "phd02": 3, "master01": 3, "master02": 3, "master03": 2, "master04": 2, "master05": 2, "under01": 2, "under02": 1},
    "PyTorch": {"phd01": 3, "phd02": 3, "master02": 2, "master03": 2, "master05": 3},
    "MATLAB": {"admin": 4, "teacher01": 3, "phd01": 3, "master01": 3, "master04": 2},
    "Simulink": {"admin": 3, "teacher01": 3, "master01": 2, "master04": 2},
    "CarSim": {"admin": 3, "phd01": 3, "master01": 2, "under02": 1},
    "车辆动力学": {"admin": 4, "teacher01": 4, "phd01": 3, "phd02": 3, "master01": 2, "master04": 2},
    "控制理论": {"admin": 4, "teacher01": 3, "phd01": 3, "master01": 2, "master05": 2},
    "数据处理": {"phd02": 3, "master03": 3, "under01": 3, "master04": 2},
    "论文写作": {"admin": 4, "teacher01": 4, "phd01": 2, "phd02": 2, "master01": 1},
    "实车实验": {"teacher01": 3, "phd01": 2, "under02": 3, "master04": 2},
}

LEARNING_PLANS = {
    "phd01": [
        ("完成轮胎垂向刚度辨识算法复现", "复现 IEEE T-IE 论文中的递推辨识算法", "理论学习", "2026-08-31", "2026-10-15", PlanStatus.IN_PROGRESS, 40),
        ("Myhil-1.0 试验台架上手", "学习台架操作规程并完成两次标定", "实验技能", "2026-09-01", "2026-10-30", PlanStatus.IN_PROGRESS, 20),
    ],
    "phd02": [
        ("UKF 与 EKF 对比实验", "在仿真环境中对比两种滤波器的收敛性", "仿真实验", "2026-09-01", "2026-10-01", PlanStatus.IN_PROGRESS, 55),
    ],
    "master01": [
        ("学习 CarSim-Simulink 联合仿真", "跑通横摆稳定性控制联合仿真 demo", "仿真工具", "2026-09-05", "2026-11-01", PlanStatus.IN_PROGRESS, 30),
        ("重读《车辆动力学及控制》第3-5章", "整理读书笔记", "理论学习", "2026-09-01", "2026-10-20", PlanStatus.IN_PROGRESS, 45),
    ],
    "master02": [
        ("强化学习基础课程", "完成 Spinning Up 教程", "理论学习", "2026-08-15", "2026-09-30", PlanStatus.BLOCKED, 60),
    ],
    "master03": [
        ("多传感器时间戳对齐方案调研", "调研 LIO 与相机时间同步方法", "文献调研", "2026-09-01", "2026-09-28", PlanStatus.COMPLETED, 100),
    ],
    "master04": [
        ("滑模观测器推导练习", "手推常见滑模观测器并仿真验证", "理论学习", "2026-09-10", "2026-11-10", PlanStatus.IN_PROGRESS, 15),
    ],
    "master05": [
        ("Gym 环境封装练习", "封装车辆二自由度 Gym 环境", "编程训练", "2026-09-01", "2026-10-15", PlanStatus.IN_PROGRESS, 35),
    ],
    "under01": [
        ("Python 数据处理入门", "numpy/pandas 基础", "编程训练", "2026-09-01", "2026-11-30", PlanStatus.IN_PROGRESS, 25),
    ],
    "under02": [
        ("实车数据采集跟车学习", "跟随师兄完成两轮采集", "实验技能", "2026-09-15", "2026-12-01", PlanStatus.NOT_STARTED, 0),
    ],
}


def _get_or_create_skill(db: Session, name: str, category: str, desc: str, order: int) -> Skill:
    skill = db.scalar(select(Skill).where(Skill.name == name))
    if skill is None:
        skill = Skill(name=name, category=category, description=desc, sort_order=order)
        db.add(skill)
        db.flush()
    return skill


def seed_domain(db: Session, users: dict) -> None:
    profiles: dict[str, MemberProfile] = {
        u.username: u.member_profile for u in users.values() if u.member_profile
    }

    # ---- skills ----
    skills: dict[str, Skill] = {}
    for name, category, desc, order in SKILLS:
        skills[name] = _get_or_create_skill(db, name, category, desc, order)

    existing_pairs = set(
        db.execute(select(MemberSkill.member_id, MemberSkill.skill_id)).all()
    )
    created = 0
    for skill_name, levels in MEMBER_SKILLS.items():
        skill = skills[skill_name]
        for username, level in levels.items():
            profile = profiles.get(username)
            if not profile:
                continue
            if (profile.id, skill.id) in existing_pairs:
                continue
            db.add(MemberSkill(member_id=profile.id, skill_id=skill.id, level=level))
            created += 1
    db.flush()
    logger.info("member_skills: +%d", created)

    # ---- learning plans ----
    plan_count = 0
    for username, plans in LEARNING_PLANS.items():
        profile = profiles.get(username)
        if not profile:
            continue
        for title, desc, category, start, target, status, progress in plans:
            if db.scalar(select(LearningPlan).where(LearningPlan.title == title)):
                continue
            db.add(
                LearningPlan(
                    member_id=profile.id,
                    title=title,
                    description=desc,
                    category=category,
                    start_date=date.fromisoformat(start),
                    target_date=date.fromisoformat(target),
                    status=status,
                    progress=progress,
                    created_by=users[username].id,
                )
            )
            plan_count += 1
    db.flush()
    logger.info("learning_plans: +%d", plan_count)

    db.commit()
    logger.info("seed_domain (M2 scope) done")
