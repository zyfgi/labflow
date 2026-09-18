import { createRouter, createWebHistory } from 'vue-router'
import { TOKEN_KEY } from '@/api/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: 'Dashboard', menu: 'dashboard' },
        },
        {
          path: 'members',
          name: 'members',
          component: () => import('@/views/member/MembersView.vue'),
          meta: { title: '成员列表', menu: 'member-list', roles: ['PI', 'TEACHER'] },
        },
        {
          path: 'members/:id',
          name: 'member-detail',
          component: () => import('@/views/member/MemberDetailView.vue'),
          meta: { title: '成员详情', menu: 'member-list' },
        },
        {
          path: 'skills-matrix',
          name: 'skills-matrix',
          component: () => import('@/views/member/SkillsMatrixView.vue'),
          meta: { title: '技能矩阵', menu: 'member-skills' },
        },
        {
          path: 'learning-plans',
          name: 'learning-plans',
          component: () => import('@/views/member/LearningPlansView.vue'),
          meta: { title: '学习计划', menu: 'member-plans' },
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('@/views/project/ProjectsView.vue'),
          meta: { title: '项目', menu: 'projects' },
        },
        {
          path: 'projects/:id',
          name: 'project-detail',
          component: () => import('@/views/project/ProjectDetailView.vue'),
          meta: { title: '项目详情', menu: 'projects' },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/task/TasksView.vue'),
          meta: { title: '任务', menu: 'tasks' },
        },
        {
          path: 'tasks/:id',
          name: 'task-detail',
          component: () => import('@/views/task/TaskDetailView.vue'),
          meta: { title: '任务详情', menu: 'tasks' },
        },
        {
          path: 'experiments',
          name: 'experiments',
          component: () => import('@/views/experiment/ExperimentsView.vue'),
          meta: { title: '实验记录', menu: 'experiments' },
        },
        {
          path: 'experiments/:id',
          name: 'experiment-detail',
          component: () => import('@/views/experiment/ExperimentDetailView.vue'),
          meta: { title: '实验详情', menu: 'experiments' },
        },
        {
          path: 'equipment',
          name: 'equipment',
          component: () => import('@/views/equipment/EquipmentView.vue'),
          meta: { title: '设备台账', menu: 'equipment' },
        },
        {
          path: 'equipment/:id',
          name: 'equipment-detail',
          component: () => import('@/views/equipment/EquipmentDetailView.vue'),
          meta: { title: '设备详情', menu: 'equipment' },
        },
        {
          path: 'equipment-bookings',
          name: 'equipment-bookings',
          component: () => import('@/views/equipment/BookingsView.vue'),
          meta: { title: '设备预约', menu: 'bookings' },
        },
        {
          path: 'equipment-borrows',
          name: 'equipment-borrows',
          component: () => import('@/views/equipment/BorrowsView.vue'),
          meta: { title: '借用记录', menu: 'borrows' },
        },
        {
          path: 'equipment-maintenance',
          name: 'equipment-maintenance',
          component: () => import('@/views/equipment/MaintenanceView.vue'),
          meta: { title: '故障维修', menu: 'maintenance' },
        },
        {
          path: 'ai',
          name: 'ai-assistant',
          component: () => import('@/views/ai/AIAssistantView.vue'),
          meta: { title: 'AI 助手', menu: 'ai' },
        },
        {
          path: 'notifications',
          name: 'notifications',
          component: () => import('@/views/system/NotificationsView.vue'),
          meta: { title: '通知', menu: 'notifications' },
        },
        {
          path: 'system/audit-logs',
          name: 'system-audit',
          component: () => import('@/views/system/AuditLogsView.vue'),
          meta: { title: '操作日志', menu: 'system-audit', roles: ['PI'] },
        },
        {
          path: 'weekly-reports',
          name: 'weekly-reports',
          component: () => import('@/views/report/WeeklyReportsView.vue'),
          meta: { title: '周报', menu: 'reports' },
        },
        {
          path: 'system/settings',
          name: 'system-settings',
          component: () => import('@/views/system/SettingsView.vue'),
          meta: { title: '系统设置', menu: 'system-settings', roles: ['PI'] },
        },
        {
          path: 'system/users',
          name: 'system-users',
          component: () => import('@/views/system/UsersView.vue'),
          meta: { title: '用户与角色', menu: 'system', roles: ['PI'] },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue'),
          meta: { title: '个人设置', menu: 'profile' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (to.name !== 'login' && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && token) {
    return { path: '/dashboard' }
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && roles.length > 0) {
    const user = JSON.parse(localStorage.getItem('labflow_user') ?? 'null')
    if (!user || !roles.includes(user.role)) {
      return { path: '/dashboard' }
    }
  }
  return true
})

export default router
