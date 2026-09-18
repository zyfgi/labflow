"""Shared constants. Kept as plain strings so models stay portable across
PostgreSQL (production) and SQLite (local tests)."""


class Role:
    PI = "PI"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    EQUIPMENT_ADMIN = "EQUIPMENT_ADMIN"
    GUEST = "GUEST"


ALL_ROLES = [Role.PI, Role.TEACHER, Role.STUDENT, Role.EQUIPMENT_ADMIN, Role.GUEST]


class UserStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"


MEMBER_TYPES = ["teacher", "postdoc", "phd", "master", "undergraduate", "assistant"]
MEMBER_STATUSES = ["active", "graduated", "left"]

SKILL_LEVELS = {
    0: "未接触",
    1: "学习中",
    2: "可在指导下完成",
    3: "可独立完成",
    4: "可指导他人",
}


class PlanStatus:
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


PLAN_STATUSES = [
    PlanStatus.NOT_STARTED,
    PlanStatus.IN_PROGRESS,
    PlanStatus.BLOCKED,
    PlanStatus.COMPLETED,
    PlanStatus.CANCELLED,
]


class ReportStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    RETURNED = "returned"


REPORT_STATUSES = [
    ReportStatus.DRAFT,
    ReportStatus.SUBMITTED,
    ReportStatus.REVIEWED,
    ReportStatus.RETURNED,
]


class ProjectStatus:
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


PROJECT_STATUSES = [
    ProjectStatus.PLANNING,
    ProjectStatus.ACTIVE,
    ProjectStatus.PAUSED,
    ProjectStatus.COMPLETED,
    ProjectStatus.ARCHIVED,
]

PROJECT_PRIORITIES = ["low", "medium", "high", "critical"]
PROJECT_VISIBILITIES = ["private", "project_members", "lab"]

PROJECT_MEMBER_ROLES = ["owner", "manager", "researcher", "student", "observer"]


class TaskStatus:
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


TASK_STATUSES = [
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.BLOCKED,
    TaskStatus.REVIEW,
    TaskStatus.DONE,
    TaskStatus.CANCELLED,
]

TASK_PRIORITIES = ["low", "medium", "high", "critical"]


class MilestoneStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


MILESTONE_STATUSES = [
    MilestoneStatus.PENDING,
    MilestoneStatus.IN_PROGRESS,
    MilestoneStatus.COMPLETED,
    MilestoneStatus.CANCELLED,
]


class ExperimentStatus:
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


EXPERIMENT_STATUSES = [
    ExperimentStatus.DRAFT,
    ExperimentStatus.RUNNING,
    ExperimentStatus.COMPLETED,
    ExperimentStatus.FAILED,
    ExperimentStatus.ARCHIVED,
]


class EquipmentStatus:
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    BORROWED = "borrowed"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


EQUIPMENT_STATUSES = [
    EquipmentStatus.AVAILABLE,
    EquipmentStatus.RESERVED,
    EquipmentStatus.IN_USE,
    EquipmentStatus.BORROWED,
    EquipmentStatus.FAULT,
    EquipmentStatus.MAINTENANCE,
    EquipmentStatus.DISABLED,
]


class BookingStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


BOOKING_STATUSES = [
    BookingStatus.PENDING,
    BookingStatus.APPROVED,
    BookingStatus.REJECTED,
    BookingStatus.CANCELLED,
    BookingStatus.COMPLETED,
]


class BorrowStatus:
    BORROWED = "borrowed"
    RETURNED = "returned"
    OVERDUE = "overdue"


BORROW_STATUSES = [BorrowStatus.BORROWED, BorrowStatus.RETURNED, BorrowStatus.OVERDUE]


class MaintenanceStatus:
    REPORTED = "reported"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


MAINTENANCE_STATUSES = [
    MaintenanceStatus.REPORTED,
    MaintenanceStatus.PROCESSING,
    MaintenanceStatus.COMPLETED,
    MaintenanceStatus.CANCELLED,
]

MAINTENANCE_TYPES = ["fault", "maintenance", "calibration", "inspection"]
