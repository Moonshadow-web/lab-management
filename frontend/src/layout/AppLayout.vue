<template>
  <el-container class="app-container">
    <el-aside width="220px" class="aside">
      <div class="logo">生免组管理系统</div>
      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
        background-color="#1a365d"
        text-color="#cbd5e1"
        active-text-color="#ffd04b"
      >
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
          <el-tag v-if="m.wip" size="small" type="info" class="wip">建设中</el-tag>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const menus = [
  { path: '/dashboard', title: '工作台', icon: 'Odometer' },
  { path: '/test-items', title: '项目查询', icon: 'Document' },
  { path: '/documents', title: '文件管理', icon: 'Files' },
  { path: '/instruments', title: '仪器档案', icon: 'Cpu' },
  { path: '/qc', title: '质控管理', icon: 'DataLine', wip: true },
  { path: '/reagents', title: '试剂管理', icon: 'ShoppingCart', wip: true },
  { path: '/training', title: '继教培训', icon: 'Reading', wip: true },
  { path: '/verification', title: '性能验证', icon: 'DataAnalysis', wip: true },
  { path: '/iso15189', title: '15189专项', icon: 'Stamp', wip: true },
]

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '工作台')

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}
.aside {
  background: #1a365d;
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
</style>
