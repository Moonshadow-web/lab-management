<template>
  <el-container class="app-container">
    <div v-if="isMobile && drawerVisible" class="overlay" @click="drawerVisible = false"></div>
    <el-aside
      width="220px"
      class="aside"
      :class="{ 'aside-mobile': isMobile, 'aside-open': isMobile && drawerVisible }"
    >
      <div class="logo">
        生免组管理系统
        <el-icon class="close-btn" @click="drawerVisible = false" v-if="isMobile"><Close /></el-icon>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        @select="onMenuSelect"
        background-color="#1a365d"
        text-color="#cbd5e1"
        active-text-color="#ffd04b"
      >
        <template v-for="m in menus" :key="m.path">
          <el-sub-menu v-if="m.children" :index="m.path">
            <template #title>
              <el-icon><component :is="m.icon" /></el-icon>
              <span>{{ m.title }}</span>
            </template>
            <el-menu-item v-for="c in m.children" :key="c.path" :index="c.path">{{ c.title }}</el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="m.path">
            <el-icon><component :is="m.icon" /></el-icon>
            <span>{{ m.title }}</span>
            <el-tag v-if="m.wip" size="small" type="info" class="wip">建设中</el-tag>
          </el-menu-item>
        </template>
      </el-menu>
      <div class="aside-footer" v-if="auth.canAccessMenu('instrument-families') || auth.canAccessMenu('quality-requirements')">
        <el-button v-if="auth.canAccessMenu('instrument-families')" class="families-btn" size="small" :icon="Connection" @click="goEqaAssociations">项目库与质评关联</el-button>
        <el-button v-if="auth.canAccessMenu('instrument-families')" class="families-btn" size="small" :icon="Share" @click="goFamilies">仪器关联管理</el-button>
        <el-button v-if="auth.canAccessMenu('quality-requirements')" class="families-btn" size="small" :icon="Document" @click="goQualityRequirements">项目质量要求</el-button>
      </div>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-icon class="hamburger" @click="drawerVisible = true" v-if="isMobile"><Menu /></el-icon>
        <span class="title">{{ currentTitle }}</span>
        <el-dropdown @command="onCommand">
          <span class="user-info">
            {{ auth.user?.full_name || auth.user?.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { usePermissionStore } from '../store/permission'
import { Share, Connection, Document, Menu, Close } from '@element-plus/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const menus = computed(() => {
  const all = [
    { path: '/dashboard', title: '工作台', icon: 'Odometer' },
    { path: '/test-items', title: '项目查询', icon: 'Document', moduleKey: 'test-items' },
    { path: '/documents', title: '文件管理', icon: 'Files', moduleKey: 'documents' },
    { path: '/instruments', title: '仪器档案', icon: 'Cpu', moduleKey: 'instruments' },
    // 质控管理是聚合菜单：含 月结/质评/仪器间比对/室间比对/累靶 多个权限模块，任一可见即显示
    { path: '/qc', title: '质控管理', icon: 'DataLine', moduleKeys: ['qc-monthly', 'eqa', 'comparison', 'interlab', 'qc-target'] },
    { path: '/reagent', title: '试剂管理', icon: 'ShoppingCart', moduleKey: 'reagents', children: [
      { path: '/reagent/items', title: '试剂目录' },
      { path: '/reagent/stock', title: '实时库存' },
      { path: '/reagent/inventory', title: '盘库管理' },
      { path: '/reagent/orders', title: '订购管理' },
      { path: '/reagent/receivings', title: '到货接收' },
      { path: '/reagent/consumption', title: '月消耗' },
      { path: '/reagent/associations', title: '项目与仪器关联' },
    ] },
    { path: '/training', title: '继教培训', icon: 'Reading', moduleKey: 'training' },
    { path: '/verification', title: '性能验证', icon: 'DataAnalysis', moduleKey: 'verification' },
    { path: '/scheduling', title: '排班管理', icon: 'Calendar', moduleKey: 'scheduling' },
    { path: '/iso15189', title: '15189专项', icon: 'Stamp', moduleKey: 'iso15189' },
  ]
  // 按权限过滤：technical_support 仅显示其被授权的模块；其余角色维持原样（全部可见）
  const visible = all.filter((m) => {
    if (m.path === '/dashboard') return true
    if (m.moduleKeys) return auth.canAccessAnyMenu(m.moduleKeys)
    return auth.canAccessMenu(m.moduleKey)
  })
  // 管理员额外可见系统管理类
  const isAdmin = auth.user?.role === 'admin' || (auth.user?.roles || '').includes('admin')
  if (isAdmin) {
    visible.push({ path: '/users', title: '用户管理', icon: 'UserFilled' })
    visible.push({ path: '/permission-config', title: '权限配置', icon: 'Lock' })
    visible.push({ path: '/audit-logs', title: '审计日志', icon: 'View' })
    visible.push({ path: '/reminder-settings', title: '提醒设置', icon: 'Bell' })
  }
  return visible
})

const isMobile = ref(typeof window !== 'undefined' && window.innerWidth <= 768)
const drawerVisible = ref(false)
function checkMobile() {
  isMobile.value = window.innerWidth <= 768
  if (!isMobile.value) drawerVisible.value = false
}
function onMenuSelect() {
  if (isMobile.value) drawerVisible.value = false
}
onMounted(() => {
  window.addEventListener('resize', checkMobile)
  // 页面刷新场景：登录态下补一次模块权限映射（canWrite 依赖）
  if (auth.isLoggedIn) {
    try { usePermissionStore().load() } catch (_) {}
  }
})
onUnmounted(() => window.removeEventListener('resize', checkMobile))

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '工作台')

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

function goFamilies() {
  router.push('/instrument-families')
}

function goEqaAssociations() {
  router.push('/eqa-associations')
}

function goQualityRequirements() {
  router.push('/quality-requirements')
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}
.aside {
  background: #1a365d;
  display: flex;
  flex-direction: column;
}
.aside-footer {
  margin-top: auto;
  padding: 12px 14px;
  border-top: 1px solid #2c4a73;
}
.families-btn {
  width: 100%;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid #2c4a73;
  color: #cbd5e1;
}
.families-btn:hover {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  border-color: #3b5a8a;
}
.logo {
  color: #fff;
  font-weight: 700;
  padding: 18px 16px;
  font-size: 16px;
  border-bottom: 1px solid #2c4a73;
}
.menu {
  border-right: none;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}
.wip {
  margin-left: 8px;
}
/* 移动端抽屉式侧边栏 */
.aside-mobile {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 1001;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.35);
}
.aside-open {
  transform: translateX(0);
}
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
}
.hamburger {
  font-size: 22px;
  cursor: pointer;
  margin-right: 12px;
  color: #1a365d;
}
.close-btn {
  float: right;
  cursor: pointer;
  font-size: 18px;
  margin-top: 2px;
}
@media (max-width: 768px) {
  .title {
    font-size: 16px;
  }
  .el-main {
    padding: 10px;
    overflow-x: auto;
  }
}
</style>
