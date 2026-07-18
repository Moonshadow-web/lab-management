<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>权限配置 — 角色 × 模块</span>
          <div>
            <el-button size="small" :icon="Refresh" @click="load" :loading="loading">刷新</el-button>
            <el-button size="small" type="danger" :icon="RefreshLeft" @click="onReset" :loading="resetting">重置为出厂默认</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="!loaded"
        title="正在加载模块权限..."
        type="info" :closable="false" show-icon style="margin-bottom: 12px"
      />
      <el-alert
        v-else
        type="success"
        :closable="false" show-icon
        style="margin-bottom: 12px"
      >
        <template #title>
          管理员（admin）对所有模块通杀，不在本表控制范围。
          改完即时生效（其他用户刷新页面或重新登录后即按新规则判定）。
        </template>
      </el-alert>

      <el-table :data="rows" border size="small" v-loading="loading">
        <el-table-column prop="label" label="模块" width="160" fixed />
        <el-table-column prop="key" label="代码" width="160" fixed>
          <template #default="{ row }">
            <code>{{ row.key }}</code>
          </template>
        </el-table-column>
        <el-table-column label="可写角色（多选）" min-width="500">
          <template #default="{ row }">
            <el-checkbox-group v-model="row.roles" @change="(v) => onChange(row, v)">
              <el-checkbox
                v-for="r in roleOptions"
                :key="r.code"
                :value="r.code"
                :disabled="r.code === 'admin'"
              >
                {{ r.label }}
                <el-tag v-if="r.code === 'admin'" type="danger" size="small" effect="plain" style="margin-left: 4px">通杀</el-tag>
              </el-checkbox>
            </el-checkbox-group>
            <div v-if="row.saving" style="color: #909399; font-size: 12px; margin-top: 4px">
              <el-icon class="is-loading"><Loading /></el-icon> 保存中...
            </div>
            <div v-else-if="row.savedAt" style="color: #67c23a; font-size: 12px; margin-top: 4px">
              <el-icon><Check /></el-icon> 已保存 · {{ row.savedAt }} · {{ row.savedBy }}
            </div>
            <div v-else-if="row.error" style="color: #f56c6c; font-size: 12px; margin-top: 4px">
              保存失败：{{ row.error }}
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, RefreshLeft, Loading, Check } from '@element-plus/icons-vue'
import { getModulePermissionsStructure, setModuleRoles, resetModulePermissions } from '../../api/modulePermissions'
import { usePermissionStore } from '../../store/permission'

const permStore = usePermissionStore()
const loaded = ref(false)
const loading = ref(false)
const resetting = ref(false)
const modules = ref([])   // [{key, label, roles: [code]}]
const roleOptions = ref([]) // [{code, label}]

const rows = computed(() => modules.value.map((m) => ({ ...m, saving: false, savedAt: '', savedBy: '', error: '' })))

async function load() {
  loading.value = true
  try {
    const r = await getModulePermissionsStructure()
    modules.value = r.data.modules
    roleOptions.value = r.data.roles
    loaded.value = true
    // 同步到全局 store，让其他模块的 canWrite 立即用新值
    for (const m of r.data.modules) {
      permStore.setLocal(m.key, m.roles)
    }
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function onChange(row, roles) {
  // 强制包含 admin（前端显示虽 disabled，但 API 层也会兜底）
  if (!roles.includes('admin')) roles = ['admin', ...roles]
  row.saving = true
  row.savedAt = ''
  row.savedBy = ''
  row.error = ''
  try {
    await setModuleRoles(row.key, roles)
    row.savedAt = new Date().toLocaleTimeString('zh-CN')
    row.savedBy = (JSON.parse(localStorage.getItem('user') || 'null')?.username) || ''
    // 同步到全局
    permStore.setLocal(row.key, roles)
    ElMessage.success(`「${row.label}」权限已更新`)
  } catch (e) {
    row.error = e?.response?.data?.detail || e.message
    ElMessage.error('保存失败：' + row.error)
  } finally {
    row.saving = false
  }
}

async function onReset() {
  try {
    await ElMessageBox.confirm(
      '将清空所有自定义权限配置，恢复为出厂默认值。**不可恢复**，确定继续？',
      '重置为出厂默认',
      { type: 'error', confirmButtonText: '确认重置', cancelButtonText: '取消' }
    )
  } catch { return }
  resetting.value = true
  try {
    await resetModulePermissions()
    ElMessage.success('已重置为出厂默认')
    await load()
  } catch (e) {
    ElMessage.error('重置失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    resetting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
code {
  background: #f5f7fa; padding: 1px 6px; border-radius: 3px;
  font-family: Consolas, Monaco, 'Courier New', monospace; font-size: 12px;
  color: #606266;
}
</style>
