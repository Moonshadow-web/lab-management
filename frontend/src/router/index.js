import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { usePermissionStore } from '../store/permission'
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
      { path: 'test-items', name: 'test-items', component: () => import('../views/test_items/TestItemList.vue'), meta: { title: '项目查询', moduleKey: 'test-items' } },
      { path: 'documents', name: 'documents', component: () => import('../views/documents/DocumentList.vue'), meta: { title: '文件管理', moduleKey: 'documents' } },
      { path: 'instruments', name: 'instruments', component: () => import('../views/instruments/InstrumentList.vue'), meta: { title: '仪器档案', moduleKey: 'instruments' } },
      { path: 'instrument-families', name: 'instrument-families', component: () => import('../views/instruments/InstrumentFamilyManage.vue'), meta: { title: '仪器关联', moduleKey: 'instrument-families' } },
      { path: 'qc', name: 'qc', component: () => import('../views/qc/QCList.vue'), meta: { title: '质控管理', moduleKeys: ['qc-monthly', 'eqa', 'comparison', 'interlab', 'qc-target'] } },
      { path: 'eqa-associations', name: 'eqa-associations', component: () => import('../views/eqa/EqaAssociationManage.vue'), meta: { title: '项目库与质评关联', moduleKey: 'instrument-families' } },
      { path: 'quality-requirements', name: 'quality-requirements', component: () => import('../views/quality/QualityRequirementList.vue'), meta: { title: '项目质量要求', moduleKey: 'quality-requirements' } },
      { path: 'reagent/items', name: 'reagent-items', component: () => import('../views/reagent/ReagentItems.vue'), meta: { title: '试剂目录', moduleKey: 'reagents' } },
      { path: 'reagent/stock', name: 'reagent-stock', component: () => import('../views/reagent/ReagentStock.vue'), meta: { title: '实时库存', moduleKey: 'reagents' } },
      { path: 'reagent/inventory', name: 'reagent-inventory', component: () => import('../views/reagent/InventoryCheck.vue'), meta: { title: '盘库管理', moduleKey: 'reagents' } },
      { path: 'reagent/orders', name: 'reagent-orders', component: () => import('../views/reagent/ReagentOrders.vue'), meta: { title: '订购管理', moduleKey: 'reagents' } },
      { path: 'reagent/receivings', name: 'reagent-receivings', component: () => import('../views/reagent/ReagentReceivings.vue'), meta: { title: '到货接收', moduleKey: 'reagents' } },
      { path: 'reagent/consumption', name: 'reagent-consumption', component: () => import('../views/reagent/ReagentConsumption.vue'), meta: { title: '月消耗', moduleKey: 'reagents' } },
      { path: 'training', name: 'training', component: () => import('../views/training/TrainingList.vue'), meta: { title: '继教培训', moduleKey: 'training' } },
      { path: 'verification', name: 'verification', component: () => import('../views/verification/VerificationList.vue'), meta: { title: '性能验证', moduleKey: 'verification' } },
      { path: 'iso15189', name: 'iso15189', component: () => import('../views/iso15189/NonconformityList.vue'), meta: { title: '15189专项', moduleKey: 'iso15189' } },
      { path: 'audit-logs', name: 'audit-logs', component: () => import('../views/audit/AuditLogList.vue'), meta: { title: '审计日志', adminOnly: true } },
      { path: 'users', name: 'users', component: () => import('../views/users/UserList.vue'), meta: { title: '用户管理', adminOnly: true } },
      { path: 'permission-config', name: 'permission-config', component: () => import('../views/users/PermissionsConfig.vue'), meta: { title: '权限配置', adminOnly: true } },
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
  } else if (to.meta.moduleKeys || to.meta.moduleKey) {
    // 模块级守卫：仅 technical_support 严格收口（未授权模块不可直达）；
    // 其余角色 canAccessMenu 恒为 true，不受影响。
    const keys = to.meta.moduleKeys || [to.meta.moduleKey]
    if (auth.canAccessAnyMenu(keys)) {
      next()
    } else {
      next('/dashboard')
    }
  } else {
    next()
  }
})

export default router
