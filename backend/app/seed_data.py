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
    "Python": {
        "admin": 4,
        "teacher01": 4,
        "phd01": 4,
        "phd02": 3,
        "master01": 3,
        "master02": 3,
        "master03": 2,
        "master04": 2,
        "master05": 2,
        "under01": 2,
        "under02": 1,
    },
    "PyTorch": {"phd01": 3, "phd02": 3, "master02": 2, "master03": 2, "master05": 3},
    "MATLAB": {"admin": 4, "teacher01": 3, "phd01": 3, "master01": 3, "master04": 2},
    "Simulink": {"admin": 3, "teacher01": 3, "master01": 2, "master04": 2},
    "CarSim": {"admin": 3, "phd01": 3, "master01": 2, "under02": 1},
    "车辆动力学": {
        "admin": 4,
        "teacher01": 4,
        "phd01": 3,
        "phd02": 3,
        "master01": 2,
        "master04": 2,
    },
    "控制理论": {"admin": 4, "teacher01": 3, "phd01": 3, "master01": 2, "master05": 2},
    "数据处理": {"phd02": 3, "master03": 3, "under01": 3, "master04": 2},
    "论文写作": {"admin": 4, "teacher01": 4, "phd01": 2, "phd02": 2, "master01": 1},
    "实车实验": {"teacher01": 3, "phd01": 2, "under02": 3, "master04": 2},
}

LEARNING_PLANS = {
    "phd01": [
        (
            "完成轮胎垂向刚度辨识算法复现",
            "复现 IEEE T-IE 论文中的递推辨识算法",
            "理论学习",
            "2026-08-31",
            "2026-10-15",
            PlanStatus.IN_PROGRESS,
            40,
        ),
        (
            "Myhil-1.0 试验台架上手",
            "学习台架操作规程并完成两次标定",
            "实验技能",
            "2026-09-01",
            "2026-10-30",
            PlanStatus.IN_PROGRESS,
            20,
        ),
    ],
    "phd02": [
        (
            "UKF 与 EKF 对比实验",
            "在仿真环境中对比两种滤波器的收敛性",
            "仿真实验",
            "2026-09-01",
            "2026-10-01",
            PlanStatus.IN_PROGRESS,
            55,
        ),
    ],
    "master01": [
        (
            "学习 CarSim-Simulink 联合仿真",
            "跑通横摆稳定性控制联合仿真 demo",
            "仿真工具",
            "2026-09-05",
            "2026-11-01",
            PlanStatus.IN_PROGRESS,
            30,
        ),
        (
            "重读《车辆动力学及控制》第3-5章",
            "整理读书笔记",
            "理论学习",
            "2026-09-01",
            "2026-10-20",
            PlanStatus.IN_PROGRESS,
            45,
        ),
    ],
    "master02": [
        (
            "强化学习基础课程",
            "完成 Spinning Up 教程",
            "理论学习",
            "2026-08-15",
            "2026-09-30",
            PlanStatus.BLOCKED,
            60,
        ),
    ],
    "master03": [
        (
            "多传感器时间戳对齐方案调研",
            "调研 LIO 与相机时间同步方法",
            "文献调研",
            "2026-09-01",
            "2026-09-28",
            PlanStatus.COMPLETED,
            100,
        ),
    ],
    "master04": [
        (
            "滑模观测器推导练习",
            "手推常见滑模观测器并仿真验证",
            "理论学习",
            "2026-09-10",
            "2026-11-10",
            PlanStatus.IN_PROGRESS,
            15,
        ),
    ],
    "master05": [
        (
            "Gym 环境封装练习",
            "封装车辆二自由度 Gym 环境",
            "编程训练",
            "2026-09-01",
            "2026-10-15",
            PlanStatus.IN_PROGRESS,
            35,
        ),
    ],
    "under01": [
        (
            "Python 数据处理入门",
            "numpy/pandas 基础",
            "编程训练",
            "2026-09-01",
            "2026-11-30",
            PlanStatus.IN_PROGRESS,
            25,
        ),
    ],
    "under02": [
        (
            "实车数据采集跟车学习",
            "跟随师兄完成两轮采集",
            "实验技能",
            "2026-09-15",
            "2026-12-01",
            PlanStatus.NOT_STARTED,
            0,
        ),
    ],
}


def _get_or_create_skill(
    db: Session, name: str, category: str, desc: str, order: int
) -> Skill:
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

    # ---- weekly reports (relative to today so demo data always looks fresh) ----
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)

    def report(member_username: str, week_start: date, status: str, **fields) -> None:
        profile = profiles.get(member_username)
        if not profile:
            return
        if db.scalar(
            select(WeeklyReport).where(
                WeeklyReport.member_id == profile.id,
                WeeklyReport.week_start == week_start,
            )
        ):
            return
        reviewer = fields.pop("reviewer", users["admin"])
        review_comment = fields.pop("review_comment", None)
        reviewed_at = fields.pop("reviewed_at", None)
        db.add(
            WeeklyReport(
                member_id=profile.id,
                week_start=week_start,
                week_end=week_start + timedelta(days=6),
                status=status,
                submitted_at=fields.pop(
                    "submitted_at",
                    datetime.combine(
                        week_start + timedelta(days=4), datetime.min.time()
                    ),
                ),
                reviewer_id=reviewer.id if reviewed_at else None,
                reviewed_at=reviewed_at,
                review_comment=review_comment,
                **fields,
            )
        )

    report(
        "master01",
        this_monday,
        ReportStatus.SUBMITTED,
        work_summary="完成 CarSim 联合仿真 demo 搭建",
        learning_summary="学习整车七自由度模型",
        problems="转向阶跃工况发散",
        next_week_plan="调整轮胎模型参数",
        self_progress=45,
    )
    report(
        "master01",
        last_monday,
        ReportStatus.REVIEWED,
        work_summary="阅读横摆稳定性文献 5 篇",
        learning_summary="整理 LQR 基础",
        next_week_plan="搭建 Simulink 模型",
        self_progress=35,
        reviewer=users["admin"],
        review_comment="继续，注意对比不同控制增益",
        reviewed_at=datetime.combine(
            last_monday + timedelta(days=6), datetime.min.time()
        ),
    )
    report(
        "phd01",
        this_monday,
        ReportStatus.SUBMITTED,
        work_summary="完成垂向刚度辨识算法复现，误差 8%",
        learning_summary="递推最小二乘推导",
        experiment_summary="Myhil 台架第一次标定",
        problems="采样频率不足",
        next_week_plan="升级采集卡驱动",
        self_progress=60,
    )
    report(
        "phd01",
        last_monday,
        ReportStatus.REVIEWED,
        work_summary="跑通 UKF 基线",
        next_week_plan="复现论文算法",
        self_progress=50,
        reviewer=users["admin"],
        review_comment="基线数据要存档到实验记录",
        reviewed_at=datetime.combine(
            last_monday + timedelta(days=6), datetime.min.time()
        ),
    )
    report(
        "master02",
        this_monday,
        ReportStatus.RETURNED,
        work_summary="看了一些资料",
        learning_summary="rl 入门",
        problems="卡在环境配置",
        next_week_plan="继续配置环境",
        self_progress=20,
        reviewer=users["admin"],
        review_comment="周报太笼统，请写清楚具体完成了什么、卡在哪一步",
        reviewed_at=datetime.combine(
            this_monday + timedelta(days=5), datetime.min.time()
        ),
    )
    report(
        "master03",
        last_monday,
        ReportStatus.SUBMITTED,
        work_summary="完成时间戳对齐方案调研报告",
        next_week_plan="实现原型",
        self_progress=90,
        reviewer=users["teacher01"],
        review_comment="调研较全面，可以进入实现阶段",
        reviewed_at=datetime.combine(
            last_monday + timedelta(days=6), datetime.min.time()
        ),
    )
    report(
        "master04",
        this_monday,
        ReportStatus.DRAFT,
        work_summary="滑模观测器推导进行中",
        self_progress=15,
    )

    report_count = len(db.new)
    db.flush()
    logger.info("weekly_reports: +%d", report_count)

    # ---- projects / milestones / tasks ----
    from app.models.enums import MilestoneStatus

    PROJECTS = [
        {
            "code": "LAB-P001",
            "name": "车辆参数在线估计",
            "research_direction": "车辆参数与状态在线估计",
            "status": ProjectStatus.ACTIVE,
            "priority": "high",
            "progress": 45,
            "owner": "admin",
            "description": "基于多源传感的整车参数在线辨识，重点解决垂向/侧偏刚度时变估计问题。",
            "members": [
                ("phd01", "researcher"),
                ("master04", "student"),
                ("under01", "student"),
            ],
            "milestones": [
                ("完成数据采集方案", 30, MilestoneStatus.COMPLETED),
                ("辨识算法基线跑通", -14, MilestoneStatus.IN_PROGRESS),
                ("实车验证", 45, MilestoneStatus.PENDING),
            ],
            "tasks": [
                ("整理 2025 年实车采集数据", "phd01", 20, TaskStatus.DONE, -25, 10),
                ("递推最小二乘算法实现", "phd01", 55, TaskStatus.IN_PROGRESS, -10, 12),
                ("IMU 安装误差标定", "master04", 30, TaskStatus.IN_PROGRESS, -5, 20),
                ("采集数据清洗脚本", "under01", 80, TaskStatus.REVIEW, -12, 3),
                ("编写中期汇报材料", "phd01", 10, TaskStatus.TODO, None, 25),
                ("垂向刚度激励工况设计", "phd01", 0, TaskStatus.TODO, 5, 40),
            ],
        },
        {
            "code": "LAB-P002",
            "name": "轮胎力在线估计",
            "research_direction": "轮胎-路面摩擦估计",
            "status": ProjectStatus.ACTIVE,
            "priority": "critical",
            "progress": 30,
            "owner": "admin",
            "description": "基于扩展卡尔曼滤波的轮胎力在线估计，目标在低附着路面达到 90% 精度。",
            "members": [
                ("phd02", "researcher"),
                ("master03", "student"),
                ("under02", "student"),
            ],
            "milestones": [
                ("UKF/EKF 对比结论", -20, MilestoneStatus.COMPLETED),
                ("低附着工况验证", 21, MilestoneStatus.PENDING),
            ],
            "tasks": [
                ("UKF 与 EKF 收敛性对比实验", "phd02", 100, TaskStatus.DONE, -30, -12),
                ("B 类路面数据集整理", "master03", 60, TaskStatus.IN_PROGRESS, -8, 15),
                ("估计器代码工程化重构", "phd02", 25, TaskStatus.IN_PROGRESS, -6, 30),
                ("低附着标定试验申请", "under02", 0, TaskStatus.BLOCKED, None, 18),
                ("撰写轮胎力估计论文大纲", "phd02", 5, TaskStatus.TODO, None, 60),
                ("六维力传感器标定复核", "phd02", 0, TaskStatus.TODO, -1, -3),
            ],
        },
        {
            "code": "LAB-P003",
            "name": "车辆横摆稳定性控制",
            "research_direction": "底盘控制",
            "status": ProjectStatus.PLANNING,
            "priority": "medium",
            "progress": 15,
            "owner": "teacher01",
            "description": "面向分布式驱动电动汽车的横摆稳定性 LQR 控制策略研究。",
            "members": [
                ("master01", "student"),
                ("master02", "student"),
                ("master05", "student"),
            ],
            "milestones": [
                ("联合仿真环境搭建", 7, MilestoneStatus.IN_PROGRESS),
                ("控制策略初版", 60, MilestoneStatus.PENDING),
            ],
            "tasks": [
                (
                    "CarSim-Simulink 联合仿真 demo",
                    "master01",
                    40,
                    TaskStatus.IN_PROGRESS,
                    -7,
                    8,
                ),
                (
                    "二自由度模型读书笔记",
                    "master01",
                    45,
                    TaskStatus.IN_PROGRESS,
                    -3,
                    14,
                ),
                ("LQR 控制器仿真验证", "master01", 0, TaskStatus.TODO, 9, 40),
                (
                    "Spinning Up 教程复现",
                    "master02",
                    60,
                    TaskStatus.IN_PROGRESS,
                    -20,
                    13,
                ),
                ("Gym 车辆环境封装", "master05", 35, TaskStatus.IN_PROGRESS, -4, 28),
                ("调研分布式驱动控制文献", "master02", 0, TaskStatus.TODO, 2, 35),
            ],
        },
    ]

    for spec in PROJECTS:
        if db.scalar(select(Project).where(Project.code == spec["code"])):
            continue
        project = Project(
            name=spec["name"],
            code=spec["code"],
            description=spec["description"],
            research_direction=spec["research_direction"],
            status=spec["status"],
            priority=spec["priority"],
            progress=spec["progress"],
            visibility="lab",
            owner_id=users[spec["owner"]].id,
            start_date=date(2026, 3, 1),
            expected_end_date=date(2027, 3, 1),
        )
        db.add(project)
        db.flush()
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=users[spec["owner"]].id,
                project_role="owner",
            )
        )
        for username, role in spec["members"]:
            db.add(
                ProjectMember(
                    project_id=project.id, user_id=users[username].id, project_role=role
                )
            )
        today = date.today()
        for title, offset_days, status in spec["milestones"]:
            db.add(
                Milestone(
                    project_id=project.id,
                    title=title,
                    due_date=today + timedelta(days=offset_days),
                    status=status,
                    progress=100
                    if status == MilestoneStatus.COMPLETED
                    else (50 if status == MilestoneStatus.IN_PROGRESS else 0),
                )
            )
        for idx, (title, assignee, progress, status, due_offset, *_rest) in enumerate(
            spec["tasks"]
        ):
            task_due = (
                today + timedelta(days=due_offset) if due_offset is not None else None
            )
            db.add(
                Task(
                    project_id=project.id,
                    title=title,
                    description=f"seed task {spec['code']} #{idx + 1}",
                    assignee_id=users[assignee].id,
                    creator_id=users[spec["owner"]].id,
                    priority="high" if spec["priority"] == "critical" else "medium",
                    status=status,
                    progress=progress,
                    due_date=task_due,
                    completed_at=datetime.combine(
                        today - timedelta(days=1), datetime.min.time()
                    )
                    if status == TaskStatus.DONE
                    else None,
                )
            )
    db.flush()
    logger.info("projects/milestones/tasks seeded")

    # ---- experiments ----

    EXPERIMENTS = [
        (
            "LAB-P001",
            "phd01",
            "垂向刚度递推辨识验证",
            ExperimentStatus.COMPLETED,
            -18,
            "验证递推最小二乘算法对垂向刚度时变的跟踪能力",
            "Myhil-1.0 台架，采样 1kHz",
            "RLS 递推辨识，遗忘因子 0.995",
            "激励幅值 ±5mm，扫频 0.5-8Hz",
            "刚度跟踪误差 8.2%，收敛时间 12s",
            "算法可用于实车场景",
            "采样频率在高频段不足",
            "升级采集卡后重测",
            "https://git.labflow.edu.cn/est/vk-rbc",
            "a1b2c3d",
        ),
        (
            "LAB-P001",
            "phd01",
            "IMU 安装误差对辨识影响",
            ExperimentStatus.RUNNING,
            -6,
            "量化安装角误差对刚度估计的敏感度",
            "实车前轴，IMU 三只",
            "蒙特卡洛注入 ±2° 安装角",
            "500 组蒙特卡洛样本",
            None,
            None,
            "样本量大，脚本偶发内存溢出",
            "分批处理",
            None,
            None,
        ),
        (
            "LAB-P001",
            "master04",
            "滑模观测器仿真初验",
            ExperimentStatus.DRAFT,
            -2,
            "对比滑模观测器与 Luenberger 观测器",
            "Simulink 仿真",
            "滑模面线性化设计",
            "车速 20-80km/h 扫描",
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "LAB-P002",
            "phd02",
            "UKF-EKF 低附着对比",
            ExperimentStatus.COMPLETED,
            -25,
            "评估两种滤波器在 mu=0.3 路面的估计精度",
            "CarSim+Simulink 联合仿真",
            "UKF: alpha=1e-3,beta=2,kappa=0",
            "B 类路面，车速 60km/h",
            "UKF 峰值误差 12%，EKF 21%",
            "UKF 为优选方案",
            "强侧风工况发散",
            "增加自适应 Q",
            None,
            "3f4e5d6",
        ),
        (
            "LAB-P002",
            "phd02",
            "轮胎力估计器重构冒烟测试",
            ExperimentStatus.RUNNING,
            -4,
            "验证重构后代码与原算法输出一致性",
            "Docker 容器，Python 3.12",
            "模块化重构 + 回归对比",
            "回放历史数据集 3 组",
            "前两组一致",
            None,
            "第三组存在 0.3% 偏差",
            "排查单位换算",
            None,
            None,
        ),
        (
            "LAB-P002",
            "master03",
            "多源时间戳对齐验证",
            ExperimentStatus.COMPLETED,
            -9,
            "验证硬件时间戳方案的对齐精度",
            "数据采集系统 + IMU",
            "PTP 硬件时间戳",
            "1 小时连续采集",
            "对齐误差 <1ms",
            "方案可行",
            None,
            "写入技术文档",
            None,
            None,
        ),
        (
            "LAB-P003",
            "master01",
            "联合仿真环境冒烟",
            ExperimentStatus.FAILED,
            -5,
            "跑通 CarSim-Simulink 横摆控制 demo",
            "CarSim 2020 + MATLAB R2023a",
            "LQR 基础增益",
            "双移线工况",
            None,
            None,
            "CarSim S-Function 无法加载",
            "检查版本兼容性，重装接口",
            "重装后重试",
            None,
            None,
        ),
        (
            "LAB-P003",
            "master05",
            "Gym 环境阶跃响应测试",
            ExperimentStatus.DRAFT,
            -1,
            "验证二自由度 Gym 环境的动力学正确性",
            "Python 3.12 + Gymnasium",
            "阶跃转角输入",
            "60 组随机初始条件",
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    ]

    exp_created = 0
    for row in EXPERIMENTS:
        proj_code, owner, title, status, day_offset = row[:5]
        (
            objective,
            env,
            method,
            params,
            result,
            conclusion,
            problems,
            next_step,
            repo,
            commit,
        ) = (list(row[5:15]) + [None] * 10)[:10]
        proj = db.scalar(select(Project).where(Project.code == proj_code))
        if proj is None or db.scalar(
            select(Experiment).where(Experiment.title == title)
        ):
            continue
        db.add(
            Experiment(
                experiment_no=f"EXP-{(today + timedelta(days=day_offset)).strftime('%Y%m%d')}-{(exp_created % 9) + 1:04d}",
                project_id=proj.id,
                title=title,
                objective=objective,
                owner_id=users[owner].id,
                experiment_date=today + timedelta(days=day_offset),
                status=status,
                environment=env,
                method=method,
                parameters=params,
                result_summary=result,
                conclusion=conclusion,
                problems=problems,
                next_step=next_step,
                code_repo_url=repo,
                git_commit=commit,
                is_locked=status == ExperimentStatus.COMPLETED and day_offset < -20,
            )
        )
        exp_created += 1
    db.flush()
    logger.info("experiments: +%d", exp_created)

    # ---- equipment / bookings / borrows / maintenance ----
    from app.models.enums import (
        BookingStatus,
        BorrowStatus,
        MaintenanceStatus,
    )
    from app.models.equipment import (
        Equipment,
        EquipmentBooking,
        EquipmentBorrow,
        EquipmentMaintenance,
    )

    EQUIPMENT = [
        (
            "EQ-WS-001",
            "高性能工作站",
            "计算设备",
            "Dell",
            "Precision 7960",
            "available",
            "admin",
            "楼 305",
        ),
        (
            "EQ-OSC-001",
            "示波器",
            "测量仪器",
            "Tektronix",
            "MDO34",
            "available",
            "equipadmin",
            "实验室 A203",
        ),
        (
            "EQ-DAS-001",
            "数据采集系统",
            "测量仪器",
            "NI",
            "cDAQ-9178",
            "available",
            "equipadmin",
            "实验室 A203",
        ),
        (
            "EQ-IMU-001",
            "双 IMU 测试平台",
            "实验平台",
            "自研",
            "IMU-Rig v2",
            "in_use",
            "phd01",
            "实验室 B101",
        ),
        (
            "EQ-FTS-001",
            "六维力传感器",
            "传感器",
            "ATI",
            "Mini45",
            "fault",
            "phd02",
            "实车试验车",
        ),
        (
            "EQ-MTR-001",
            "电机控制器",
            "执行部件",
            "汇川",
            "IS620N",
            "available",
            "teacher01",
            "实验室 B101",
        ),
    ]
    for asset_no, name, category, maker, model, status, manager, location in EQUIPMENT:
        if db.scalar(select(Equipment).where(Equipment.asset_no == asset_no)):
            continue
        db.add(
            Equipment(
                asset_no=asset_no,
                name=name,
                category=category,
                manufacturer=maker,
                model=model,
                location=location,
                manager_id=users[manager].id,
                status=status,
                purchase_date=date(2024, 6, 1),
                booking_required=True,
                description=f"{name}（{maker} {model}）",
            )
        )
    db.flush()

    eq_map = {
        e.name: e for e in db.scalars(select(Equipment)).all() if not e.deleted_at
    }
    now = datetime.combine(today, datetime.min.time())

    def booking(
        equipment_name: str,
        username: str,
        day_offset: int,
        hour_start: int,
        hour_end: int,
        status: str,
    ) -> None:
        eq = eq_map.get(equipment_name)
        if not eq:
            return
        start = now + timedelta(days=day_offset, hours=hour_start)
        end = now + timedelta(days=day_offset, hours=hour_end)
        if db.scalar(
            select(EquipmentBooking).where(
                EquipmentBooking.equipment_id == eq.id,
                EquipmentBooking.start_time == start,
            )
        ):
            return
        db.add(
            EquipmentBooking(
                equipment_id=eq.id,
                user_id=users[username].id,
                start_time=start,
                end_time=end,
                purpose="数据采集试验"
                if username.startswith(("master", "phd", "under"))
                else "课题测试",
                status=status,
                approved_by=users["equipadmin"].id
                if status == BookingStatus.APPROVED
                else None,
                approved_at=now if status == BookingStatus.APPROVED else None,
            )
        )

    booking("示波器", "master01", 0, 9, 11, BookingStatus.APPROVED)
    booking("示波器", "master04", 0, 14, 16, BookingStatus.PENDING)
    booking("数据采集系统", "phd01", 1, 9, 12, BookingStatus.APPROVED)
    booking("数据采集系统", "phd02", 1, 10, 11, BookingStatus.PENDING)
    booking("高性能工作站", "master05", 2, 9, 18, BookingStatus.APPROVED)
    booking("双 IMU 测试平台", "phd01", 3, 13, 17, BookingStatus.PENDING)
    booking("电机控制器", "master01", 4, 9, 11, BookingStatus.COMPLETED)
    db.flush()

    def borrow(
        equipment_name: str,
        username: str,
        days_ago: int,
        return_in_days: int,
        status: str,
    ) -> None:
        eq = eq_map.get(equipment_name)
        if not eq:
            return
        if db.scalar(
            select(EquipmentBorrow).where(
                EquipmentBorrow.equipment_id == eq.id,
                EquipmentBorrow.borrow_time == now - timedelta(days=days_ago),
            )
        ):
            return
        borrow_time = now - timedelta(days=days_ago)
        expected = borrow_time + timedelta(days=return_in_days)
        db.add(
            EquipmentBorrow(
                equipment_id=eq.id,
                borrower_id=users[username].id,
                borrow_time=borrow_time,
                expected_return_time=expected,
                actual_return_time=borrow_time + timedelta(days=return_in_days - 1)
                if status == BorrowStatus.RETURNED
                else None,
                purpose="实车数据采集",
                status=status,
            )
        )

    borrow("数据采集系统", "under02", 10, 3, BorrowStatus.RETURNED)
    borrow("双 IMU 测试平台", "phd01", 2, 5, BorrowStatus.BORROWED)
    borrow("示波器", "under01", 6, 2, BorrowStatus.OVERDUE)
    db.flush()

    def maintenance(
        equipment_name: str,
        reporter: str,
        mtype: str,
        status: str,
        desc: str,
        days_ago: int,
    ) -> None:
        eq = eq_map.get(equipment_name)
        if not eq:
            return
        reported = now - timedelta(days=days_ago)
        if db.scalar(
            select(EquipmentMaintenance).where(
                EquipmentMaintenance.equipment_id == eq.id,
                EquipmentMaintenance.reported_at == reported,
            )
        ):
            return
        db.add(
            EquipmentMaintenance(
                equipment_id=eq.id,
                reporter_id=users[reporter].id,
                type=mtype,
                description=desc,
                reported_at=reported,
                started_at=reported + timedelta(hours=6)
                if status != MaintenanceStatus.REPORTED
                else None,
                finished_at=reported + timedelta(days=2)
                if status == MaintenanceStatus.COMPLETED
                else None,
                status=status,
                vendor="原厂售后" if status != MaintenanceStatus.REPORTED else None,
                cost=None,
                result="更换信号线后恢复正常"
                if status == MaintenanceStatus.COMPLETED
                else None,
            )
        )

    maintenance(
        "六维力传感器",
        "phd02",
        "fault",
        MaintenanceStatus.PROCESSING,
        "六维力传感器无输出，怀疑线缆断裂",
        3,
    )
    maintenance(
        "示波器",
        "equipadmin",
        "calibration",
        MaintenanceStatus.COMPLETED,
        "年度校准",
        30,
    )
    db.flush()
    logger.info("equipment/booking/borrow/maintenance seeded")

    db.commit()
    logger.info("seed_domain (M6 scope) done")
