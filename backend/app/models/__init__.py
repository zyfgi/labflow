"""Import all models so Base.metadata is complete for Alembic and tests."""

from app.database import Base
from app.models.ai import AIConversation, AIMessage, AIRequestLog
from app.models.equipment import (
    Equipment,
    EquipmentBooking,
    EquipmentBorrow,
    EquipmentMaintenance,
)
from app.models.experiment import Experiment, ExperimentAttachment
from app.models.learning import LearningPlan, MemberSkill, Skill
from app.models.project import Milestone, Project, ProjectMember, Task, TaskComment
from app.models.report import WeeklyReport
from app.models.system import AuditLog, Notification
from app.models.user import MemberProfile, User

__all__ = [
    "AIConversation",
    "AIMessage",
    "AIRequestLog",
    "AuditLog",
    "Base",
    "Equipment",
    "EquipmentBooking",
    "EquipmentBorrow",
    "EquipmentMaintenance",
    "Experiment",
    "ExperimentAttachment",
    "LearningPlan",
    "MemberProfile",
    "MemberSkill",
    "Milestone",
    "Notification",
    "Project",
    "ProjectMember",
    "Skill",
    "Task",
    "TaskComment",
    "User",
    "WeeklyReport",
]
