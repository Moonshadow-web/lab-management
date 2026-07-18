<template>
  <div class="user-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <div>
            <el-input v-model="searchQ" placeholder="搜索用户名/姓名" size="small" clearable style="width: 200px; margin-right: 8px" @clear="loadData" @keyup.enter="loadData" />
            <el-button size="small" :icon="Search" @click="loadData">搜索</el-button>
            <el-button size="small" type="primary" :icon="Plus" @click="onAdd">新增用户</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="perm-tabs">
        <el-tab-pane name="list" label="用户列表" />
        <el-tab-pane name="matrix" label="权限矩阵" />
      </el-tabs>

      <!-- 用户列表 tab -->
      <div v-show="activeTab === 'list'">
      <el-table :data="users" v-loading="loading" stripe size="small">
        <el-table-column prop="id" label="ID" width="50" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="full_name" label="姓名" width="80" />
        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'leader' ? 'warning' : 'info'" size="small">
              {{ ROLE_LABELS[row.role] || row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in parseRoles(row.roles)" :key="r" size="small" style="margin-right: 4px; margin-bottom: 2px">
              {{ roleLabel(r) }}
            </el-tag>
            <span v-if="!row.roles && row.role" style="color: #999; font-size: 12px">—</span>
          </template>
        </el-table-column>
        <el-table-column label="权限概览" min-width="200">
          <template #default="{ row }">
            <el-tag v-if="isAdmin(row)" type="danger" size="small" effect="dark">管理员·通杀</el-tag>
            <template v-else>
              <span style="color: #67c23a; font-weight: 600">{{ permSummary(row).count }}</span>
              <span style="color: #909399; font-size: 12px"> / {{ MODULES.length }} 模块</span>
              <div style="margin-top: 4px">
                <el-tag v-for="m in permSummary(row).mods" :key="m.key" size="small" type="success" effect="plain" style="margin-right: 3px; margin-bottom: 2px">
                  {{ m.label }}
                </el-tag>
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="改密" width="60">
          <template #default="{ row }">
            <el-tag v-if="row.must_change_password" type="danger" size="small">待改</el-tag>
            <span v-else style="color: #67c23a">✓</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="(v) => onToggleActive(row, v)" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="onShowPerm(row)">权限</el-button>
            <el-button size="small" text @click="onEditRoles(row)">角色</el-button>
            <el-button size="small" text @click="onEditInfo(row)">编辑</el-button>
            <el-button size="small" text type="warning" @click="onResetPwd(row)">重置密码</el-button>
            <el-button size="small" text type="danger" @click="onDelete(row)" :disabled="row.username === 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="loadData"
      />
      </div>

      <!-- 权限矩阵 tab -->
      <div v-show="activeTab === 'matrix'">
        <div class="matrix-tip">
          <el-icon><InfoFilled /></el-icon>
          行 = 用户，列 = 模块；✓=可写，✗=只读。带"管"字的单元格说明此用户是该模块的负责角色。
          <span style="margin-left: 12px">显示 {{ users.length }} / 共 {{ total }} 个用户</span>
        </div>
        <el-table :data="matrixRows" border size="small" style="margin-top: 8px" max-height="65vh">
          <el-table-column prop="username" label="用户名" width="120" fixed />
          <el-table-column prop="full_name" label="姓名" width="80" fixed />
          <el-table-column prop="level" label="级别" width="80" fixed>
            <template #default="{ row }">
              <el-tag :type="row.level === 'admin' ? 'danger' : row.level === 'leader' ? 'warning' : 'info'" size="small">
                {{ ROLE_LABELS[row.level] || row.level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-for="m in MODULES" :key="m.key" :label="m.label" width="92" align="center">
            <template #default="{ row }">
              <span v-if="row.isAdmin" style="color: #f56c6c; font-weight: 600">管</span>
              <span v-else-if="row.perm[m.key]" style="color: #67c23a; font-weight: 600">✓</span>
              <span v-else style="color: #c0c4cc">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 用户权限详情 -->
    <el-dialog v-model="showPerm" :title="`权限详情 - ${permUser?.full_name || ''}`" width="780px">
      <div v-if="permUser" class="perm-detail">
        <el-descriptions :column="3" border size="small" style="margin-bottom: 12px">
          <el-descriptions-item label="用户名">{{ permUser.username }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ permUser.full_name }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ permUser.department || '—' }}</el-descriptions-item>
          <el-descriptions-item label="级别">
            <el-tag :type="permUser.role === 'admin' ? 'danger' : permUser.role === 'leader' ? 'warning' : 'info'" size="small">
              {{ ROLE_LABELS[permUser.role] || permUser.role }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="角色" :span="2">
            <el-tag v-for="r in parseRoles(permUser.roles)" :key="r" size="small" style="margin-right: 4px">{{ roleLabel(r) }}</el-tag>
            <span v-if="!permUser.roles" style="color: #999">—</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="isAdmin(permUser)"
          title="管理员通杀"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          此用户是管理员，拥有所有模块的写权限
        </el-alert>
        <el-alert
          v-else
          :title="`可写 ${permDetail.count} / ${MODULES.length} 个模块`"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          基于角色 + 模块白名单计算；调整用户的角色（"角色"按钮）即可改变权限
        </el-alert>

        <el-table :data="permDetail.table" border size="small">
          <el-table-column prop="label" label="模块" width="120" />
          <el-table-column label="写权限" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.allowed" type="success" size="small">可写</el-tag>
              <el-tag v-else type="info" size="small">只读</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="依据" />
        </el-table>
      </div>
    </el-dialog>

    <!-- 新增用户 -->
    <el-dialog v-model="showAdd" title="新增用户" width="480px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="addForm.username" placeholder="如 zhangsan" />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="addForm.full_name" placeholder="如 张三" />
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option label="管理员 admin" value="admin" />
            <el-option label="组长 leader" value="leader" />
            <el-option label="职工 member" value="member" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.roleCodes" multiple placeholder="可多选" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.code" :label="r.label" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="addForm.password" placeholder="留空则默认 123456" />
          <div style="font-size: 12px; color: #999; margin-top: 4px">用户首次登录必须修改</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitAdd">确认</el-button>
      </template>
    </el-dialog>

    <!-- 编辑角色 -->
    <el-dialog v-model="showRoles" title="编辑角色" width="480px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <span>{{ editingUser?.username }} ({{ editingUser?.full_name }})</span>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="管理员 admin" value="admin" />
            <el-option label="组长 leader" value="leader" />
            <el-option label="职工 member" value="member" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.roleCodes" multiple placeholder="可多选" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.code" :label="r.label" :value="r.code" />
          </el-select>
          <div style="font-size: 12px; color: #999; margin-top: 4px">一人可兼任多个角色，保存后立即生效</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRoles = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitRoles">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑基本信息 -->
    <el-dialog v-model="showInfo" title="编辑用户" width="440px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="editForm.full_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="editForm.department" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="接收提醒的邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInfo = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitInfo">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search, Plus, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, resetPassword, getRoleOptions } from '../../api/users'
import { getModulePermissionsStructure } from '../../api/modulePermissions'
import { usePermissionStore } from '../../store/permission'

// 模块列表：启动时由 /module-permissions/structure 拉取（保留硬编码 fallback 保证首屏可用）
const FALLBACK_MODULES = [
  { key: 'test-items',          label: '项目库' },
  { key: 'documents',           label: '文件' },
  { key: 'instruments',         label: '仪器档案' },
  { key: 'instrument-families', label: '仪器关联' },
  { key: 'qc',                  label: '质控' },
  { key: 'eqa',                 label: 'EQA' },
  { key: 'reagents',            label: '试剂' },
  { key: 'training',            label: '继教' },
  { key: 'verification',        label: '性能验证' },
  { key: 'iso15189',            label: '15189' },
  { key: 'quality-requirements',label: '质量要求' },
]
const permStore = usePermissionStore()
const MODULES = ref([...FALLBACK_MODULES])

const users = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const searchQ = ref('')
const roleOptions = ref([])
const submitting = ref(false)
const activeTab = ref('list')

const showAdd = ref(false)
const showRoles = ref(false)
const showInfo = ref(false)
const showPerm = ref(false)
const permUser = ref(null)
const editingUser = ref(null)

const ROLE_LABELS = {
  admin: '管理员', leader: '组长', member: '职工',
  director: '主任', deputy_director: '副主任', quality_manager: '质量负责人',
  specialty_leader: '专业组长', qc_manager: '质控管理员', reagent_manager: '试剂管理员',
  training_manager: '继教管理员', biosafety_officer: '生物安全员', it_manager: '信息管理员',
  staff: '职工',
}

const addForm = ref({ username: '', full_name: '', role: 'member', roleCodes: [], password: '' })
const editForm = ref({ role: '', roleCodes: [], full_name: '', department: '', email: '' })

function roleLabel(code) {
  return ROLE_LABELS[code] || code
}

function parseRoles(rolesStr) {
  if (!rolesStr) return []
  return rolesStr.split(',').filter(Boolean)
}

// 把 role + roles 合并成完整角色集合（含 admin 推断）
function fullRoles(row) {
  const set = new Set()
  if (row.role) set.add(row.role)
  parseRoles(row.roles).forEach((r) => set.add(r))
  return [...set]
}

function isAdmin(row) {
  return !!(row && (row.role === 'admin' || fullRoles(row).includes('admin')))
}

// 单个模块的写权限判断（与 store/auth.js canWrite 逻辑一致）
function canWriteModule(userRoles, moduleKey) {
  if (userRoles.includes('admin')) return true
  // 优先从全局权限 store 读（admin 在配置页改后会同步到这里）
  const allowed = permStore.moduleRoles[moduleKey] || permStore.$state.moduleRoles?.[moduleKey]
  if (!allowed) return true  // 未配置白名单 = 默认允许
  return userRoles.some((r) => allowed.includes(r))
}

// 该用户能写哪些模块
function userPerms(row) {
  const roles = fullRoles(row)
  const out = {}
  for (const m of MODULES) out[m.key] = canWriteModule(roles, m.key)
  return out
}

// 主表格"权限概览"列用：哪些模块 + 数量
function permSummary(row) {
  if (isAdmin(row)) return { count: MODULES.length, mods: [] }
  const roles = fullRoles(row)
  const allowed = MODULES.filter((m) => canWriteModule(roles, m.key))
  return { count: allowed.length, mods: allowed }
}

// 权限矩阵 tab 用：行 = 用户
const matrixRows = computed(() => users.value.map((row) => ({
  ...row,
  level: row.role,
  isAdmin: isAdmin(row),
  perm: userPerms(row),
})))

// 权限详情 dialog 用：行 = 模块
const permDetail = computed(() => {
  if (!permUser.value) return { count: 0, table: [] }
  const roles = fullRoles(permUser.value)
  const table = MODULES.value.map((m) => {
    let reason = '无写权限（角色不在白名单）'
    if (isAdmin(permUser.value)) reason = '管理员：所有模块通杀'
    else if (canWriteModule(roles, m.key)) {
      const allowed = permStore.moduleRoles[m.key] || []
      const hits = roles.filter((r) => allowed.includes(r))
      reason = `角色 ${hits.map((r) => roleLabel(r)).join(' / ')} 在「${m.label}」白名单内`
    }
    return { key: m.key, label: m.label, allowed: isAdmin(permUser.value) || canWriteModule(roles, m.key), reason }
  })
  return { count: table.filter((r) => r.allowed).length, table }
})

function onShowPerm(row) {
  permUser.value = row
  showPerm.value = true
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (searchQ.value) params.q = searchQ.value
    const data = await listUsers(params)
    users.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function onAdd() {
  addForm.value = { username: '', full_name: '', role: 'member', roleCodes: [], password: '' }
  showAdd.value = true
}

async function onSubmitAdd() {
  if (!addForm.value.username || !addForm.value.full_name) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  submitting.value = true
  try {
    await createUser({
      username: addForm.value.username,
      full_name: addForm.value.full_name,
      role: addForm.value.role,
      roles: addForm.value.roleCodes.join(','),
      department: '生免组',
      is_active: true,
      password: addForm.value.password || '',
    })
    ElMessage.success('用户创建成功')
    showAdd.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

function onEditRoles(row) {
  editingUser.value = row
  editForm.value.role = row.role
  editForm.value.roleCodes = parseRoles(row.roles)
  showRoles.value = true
}

async function onSubmitRoles() {
  submitting.value = true
  try {
    await updateUser(editingUser.value.id, {
      username: editingUser.value.username,
      full_name: editingUser.value.full_name,
      role: editForm.value.role,
      roles: editForm.value.roleCodes.join(','),
      department: editingUser.value.department || '生免组',
      email: editingUser.value.email || '',
      notify_email: editingUser.value.notify_email ?? true,
      is_active: editingUser.value.is_active,
    })
    ElMessage.success('角色已更新')
    showRoles.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

function onEditInfo(row) {
  editingUser.value = row
  editForm.value.full_name = row.full_name
  editForm.value.department = row.department
  editForm.value.email = row.email
  showInfo.value = true
}

async function onSubmitInfo() {
  submitting.value = true
  try {
    await updateUser(editingUser.value.id, {
      username: editingUser.value.username,
      full_name: editForm.value.full_name,
      role: editingUser.value.role,
      roles: editingUser.value.roles || '',
      department: editForm.value.department,
      email: editForm.value.email,
      notify_email: editingUser.value.notify_email ?? true,
      is_active: editingUser.value.is_active,
    })
    ElMessage.success('信息已更新')
    showInfo.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

async function onToggleActive(row, val) {
  try {
    await updateUser(row.id, {
      username: row.username, full_name: row.full_name, role: row.role,
      roles: row.roles || '', department: row.department || '生免组',
      email: row.email || '', notify_email: row.notify_email ?? true, is_active: val,
    })
    ElMessage.success(val ? '已启用' : '已停用')
    await loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function onResetPwd(row) {
  try {
    await ElMessageBox.confirm(`确认将 ${row.full_name} 的密码重置为 123456？用户下次登录需修改密码。`, '重置密码', { type: 'warning' })
    await resetPassword(row.id)
    ElMessage.success('密码已重置为 123456')
    await loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('重置失败')
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户 ${row.username}（${row.full_name}）？此操作不可恢复。`, '删除用户', { type: 'error' })
    await deleteUser(row.id)
    ElMessage.success('用户已删除')
    await loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(async () => {
  try { roleOptions.value = await getRoleOptions() } catch {}
  // 拉最新模块结构（同步到全局 store + 本地 MODULES 列表）
  try {
    const r = await getModulePermissionsStructure()
    if (r?.modules?.length) {
      MODULES.value = r.modules.map((m) => ({ key: m.key, label: m.label }))
      for (const m of r.modules) permStore.setLocal(m.key, m.roles)
    }
  } catch {}
  await loadData()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.perm-tabs { margin-bottom: 8px; }
.perm-tabs :deep(.el-tabs__header) { margin-bottom: 4px; }
.matrix-tip {
  display: flex; align-items: center; gap: 6px;
  background: #f5f7fa; padding: 8px 12px; border-radius: 4px;
  color: #606266; font-size: 13px;
}
.perm-detail { padding: 0 4px; }
</style>
