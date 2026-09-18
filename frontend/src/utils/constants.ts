// 统一状态语义颜色（轻流程协同）:
// success=正常完成/可用, warning=需关注(受阻/维修/临期),
// danger=真正异常(故障/逾期), info=新动态/草稿/归档, primary=active/in_progress
export type TagType = 'success' | 'warning' | 'danger' | 'info' | 'primary'

export const ROLE_LABELS: Record<string, string> = {
  PI: 'PI/负责人',
  TEACHER: '教师/博后',
  STUDENT: '学生',
  EQUIPMENT_ADMIN: '设备管理员',
  GUEST: '访客',
}

export const USER_STATUS_LABELS: Record<string, TagType> = {
  active: 'success',
  inactive: 'info',
}

export const MEMBER_TYPE_LABELS: Record<string, string> = {
  teacher: '教师',
  postdoc: '博士后',
  phd: '博士生',
  master: '硕士生',
  undergraduate: '本科生',
  assistant: '助理',
}

export const MEMBER_STATUS_LABELS: Record<string, TagType> = {
  active: 'success',
  graduated: 'info',
  left: 'info',
}

export const PLAN_STATUS_LABELS: Record<string, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  blocked: '受阻',
  completed: '已完成',
  cancelled: '已取消',
}

export const PLAN_STATUS_TAGS: Record<string, TagType> = {
  not_started: 'info',
  in_progress: 'primary',
  blocked: 'warning',
  completed: 'success',
  cancelled: 'info',
}

export const REPORT_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
}

export const REPORT_STATUS_TAGS: Record<string, TagType> = {
  draft: 'info',
  published: 'success',
}

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  planning: '规划中',
  active: '进行中',
  paused: '暂停',
  completed: '已完成',
  archived: '已归档',
}

export const PROJECT_STATUS_TAGS: Record<string, TagType> = {
  planning: 'info',
  active: 'primary',
  paused: 'info',
  completed: 'success',
  archived: 'info',
}

export const PRIORITY_LABELS: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '紧急',
}

export const PRIORITY_TAGS: Record<string, TagType> = {
  low: 'info',
  medium: 'primary',
  high: 'warning',
  critical: 'danger',
}

export const MILESTONE_STATUS_LABELS: Record<string, string> = {
  pending: '未开始',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
}

export const MILESTONE_STATUS_TAGS: Record<string, TagType> = {
  pending: 'info',
  in_progress: 'primary',
  completed: 'success',
  cancelled: 'info',
}

export const TASK_STATUS_LABELS: Record<string, string> = {
  todo: '待开始',
  in_progress: '进行中',
  blocked: '受阻',
  done: '已完成',
  cancelled: '已取消',
}

export const TASK_STATUS_TAGS: Record<string, TagType> = {
  todo: 'info',
  in_progress: 'primary',
  blocked: 'warning',
  done: 'success',
  cancelled: 'info',
}

export const EXPERIMENT_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
  archived: '已归档',
}

export const EXPERIMENT_STATUS_TAGS: Record<string, TagType> = {
  draft: 'info',
  running: 'primary',
  completed: 'success',
  failed: 'danger',
  archived: 'info',
}

export const EQUIPMENT_STATUS_LABELS: Record<string, string> = {
  available: '可用',
  reserved: '已预约',
  in_use: '使用中',
  borrowed: '已借出',
  fault: '故障',
  maintenance: '维修中',
  disabled: '停用',
}

export const EQUIPMENT_STATUS_TAGS: Record<string, TagType> = {
  available: 'success',
  reserved: 'warning',
  in_use: 'primary',
  borrowed: 'primary',
  fault: 'danger',
  maintenance: 'warning',
  disabled: 'info',
}

export const BOOKING_STATUS_LABELS: Record<string, string> = {
  reserved: '已预约',
  cancelled: '已取消',
  completed: '已完成',
}

export const BOOKING_STATUS_TAGS: Record<string, TagType> = {
  reserved: 'primary',
  cancelled: 'info',
  completed: 'success',
}

export const BORROW_STATUS_LABELS: Record<string, string> = {
  borrowed: '借出中',
  returned: '已归还',
  overdue: '已逾期',
}

export const BORROW_STATUS_TAGS: Record<string, TagType> = {
  borrowed: 'primary',
  returned: 'success',
  overdue: 'danger',
}

export const MAINTENANCE_STATUS_LABELS: Record<string, string> = {
  reported: '已上报',
  processing: '处理中',
  completed: '已完成',
  cancelled: '已取消',
}

export const MAINTENANCE_STATUS_TAGS: Record<string, TagType> = {
  reported: 'warning',
  processing: 'primary',
  completed: 'success',
  cancelled: 'info',
}

export const MAINTENANCE_TYPE_LABELS: Record<string, string> = {
  fault: '故障',
  maintenance: '保养',
  calibration: '校准',
  inspection: '巡检',
}

// 通知事件分组（轻流程：通知替代审批，仅已读/未读，无需确认）
export const NOTIFICATION_GROUPS: { label: string; types: string[] }[] = [
  { label: '项目与任务', types: ['project_created', 'project_member_added', 'task_assigned', 'task_reassigned', 'task_due_changed', 'task_completed', 'task_due_soon', 'task_overdue'] },
  { label: '周报', types: ['weekly_report_published', 'weekly_report_updated', 'weekly_report_commented'] },
  { label: '实验', types: ['experiment_created', 'experiment_updated', 'experiment_locked', 'experiment_unlocked'] },
  { label: '设备', types: ['equipment_booked', 'equipment_booking_cancelled', 'equipment_borrowed', 'equipment_returned', 'equipment_overdue', 'equipment_fault', 'maintenance_updated'] },
  { label: '微信', types: ['wechat_bound', 'wechat_unbound'] },
]

export const NOTIFICATION_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  NOTIFICATION_GROUPS.flatMap((g) => g.types.map((t) => [t, g.label])),
)
