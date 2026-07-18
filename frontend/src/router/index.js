import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import AppLayout from '../layout/AppLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: AppLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'test-items', name: 'test-items', component: () => import('../views/test_items/TestItemList.vue'), meta: { title: '项目查询' } },
      { path: 'documents', name: 'documents', component: () => import('../views/documents/DocumentList.vue'), meta: { title: '文件管理' } },
      { path: 'instruments', name: 'instruments', component: () => import('../views/instruments/InstrumentList.vue'), meta: { title: '仪器档案' } },
      { path: 'instrument-families', name: 'instrument-families', component: () => import('../views/instruments/InstrumentFamilyManage.vue'), meta: { title: '仪器关联' } },
      { path: 'qc', name: 'qc', component: () => import('../views/qc/QCList.vue'), meta: { title: '质控管理' } },
      { path: 'eqa-associations', name: 'eqa-associations', component: () => import('../views/eqa/EqaAssociationManage.vue'), meta: { title: '项目库与质评关联' } },
      { path: 'quality-requirements', name: 'quality-requirements', component: () => import('../views/quality/QualityRequirementList.vue'), meta: { title: '项目质量要求' } },
      { path: 'reagents', name: 'reagents', component: () => import('../views/reagents/ReagentList.vue'), meta: { title: '试剂管理' } },
      { path: 'training', name: 'training', component: () => import('../views/training/TrainingList.vue'), meta: { title: '继教培训' } },
      { path: 'verification', name: 'verification', component: () => import('../views/verification/VerificationList.vue'), meta: { title: '性能验证' } },
      { path: 'iso15189', name: 'iso15189', component: () => import('../views/iso15189/NonconformityList.vue'), meta: { title: '15189专项' } },
      { path: 'audit-logs', name: 'audit-logs', component: () => import('../views/audit/AuditLogList.vue'), meta: { title: '审计日志', adminOnly: true } },
      { path: 'users', name: 'users', component: () => import('../views/users/UserList.vue'), meta: { title: '用户管理', adminOnly: true } },
      { path: 'reminder-settings', name: 'reminder-settings', component: () => import('../views/ReminderSettings.vue'), meta: { title: '提醒设置', adminOnly: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && auth.isLoggedIn) {
    next('/dashboard')
  } else if (to.meta.adminOnly) {
    // adminOnly 路由仅管理员可访问
    const isAdmin = auth.user?.role === 'admin' || (auth.user?.roles || '').includes('admin')
    if (!isAdmin) {
      next('/dashboard')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
