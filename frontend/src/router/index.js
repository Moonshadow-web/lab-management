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
      { path: 'qc', name: 'qc', component: () => import('../views/Placeholder.vue'), meta: { title: '质控管理', wip: true } },
      { path: 'reagents', name: 'reagents', component: () => import('../views/Placeholder.vue'), meta: { title: '试剂管理', wip: true } },
      { path: 'training', name: 'training', component: () => import('../views/Placeholder.vue'), meta: { title: '继教培训', wip: true } },
      { path: 'verification', name: 'verification', component: () => import('../views/Placeholder.vue'), meta: { title: '性能验证', wip: true } },
      { path: 'iso15189', name: 'iso15189', component: () => import('../views/Placeholder.vue'), meta: { title: '15189专项', wip: true } },
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
  } else {
    next()
  }
})

export default router
