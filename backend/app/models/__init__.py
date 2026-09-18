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
from app.models.report import WeeklyReport, WeeklyReportComment
from app.models.settings import SystemSettings
from app.models.system import AuditLog, Notification
from app.models.user import MemberProfile, User
from app.models.wechat import WeChatBindingCode

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
    "SystemSettings",
    "Task",
    "TaskComment",
    "User",
    "WeChatBindingCode",
    "WeeklyReport",
    "WeeklyReportComment",
]
