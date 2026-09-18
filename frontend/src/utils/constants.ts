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
export const NOTIFICATION_GROUPS: { label: string; types: { value: string; label: string }[] }[] = [
  {
    label: '项目与任务',
    types: [
      { value: 'project_created', label: '项目创建' },
      { value: 'project_member_added', label: '加入项目' },
      { value: 'task_assigned', label: '任务分配' },
      { value: 'task_reassigned', label: '任务改派' },
      { value: 'task_due_changed', label: '截止变更' },
      { value: 'task_completed', label: '任务完成' },
      { value: 'task_due_soon', label: '任务临期' },
      { value: 'task_overdue', label: '任务逾期' },
    ],
  },
  {
    label: '周报',
    types: [
      { value: 'weekly_report_published', label: '周报发布' },
      { value: 'weekly_report_updated', label: '周报更新' },
      { value: 'weekly_report_commented', label: '周报评论' },
    ],
  },
  {
    label: '实验',
    types: [
      { value: 'experiment_created', label: '实验创建' },
      { value: 'experiment_updated', label: '实验更新' },
      { value: 'experiment_locked', label: '实验锁定' },
      { value: 'experiment_unlocked', label: '实验解锁' },
    ],
  },
  {
    label: '设备',
    types: [
      { value: 'equipment_booked', label: '设备预约' },
      { value: 'equipment_booking_cancelled', label: '预约取消' },
      { value: 'equipment_borrowed', label: '设备借出/延期' },
      { value: 'equipment_returned', label: '设备归还' },
      { value: 'equipment_overdue', label: '借用逾期' },
      { value: 'equipment_fault', label: '故障上报' },
      { value: 'maintenance_updated', label: '维修进度' },
    ],
  },
  {
    label: '微信',
    types: [
      { value: 'wechat_bound', label: '微信绑定' },
      { value: 'wechat_unbound', label: '微信解绑' },
    ],
  },
]

export const NOTIFICATION_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  NOTIFICATION_GROUPS.flatMap((g) => g.types.map((t) => [t.value, t.label])),
)
