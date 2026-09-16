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
          meta: { title: '成员列表', menu: 'member-list', roles: ['PI', 'TEACHER', 'EQUIPMENT_ADMIN'] },
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
