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
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="r in parseRoles(row.roles)" :key="r" size="small" style="margin-right: 4px; margin-bottom: 2px">
              {{ roleLabel(r) }}
            </el-tag>
            <span v-if="!row.roles && row.role" style="color: #999; font-size: 12px">—</span>
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
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
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
    </el-card>

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
import { ref, onMounted } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, resetPassword, getRoleOptions } from '../../api/users'

const users = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const searchQ = ref('')
const roleOptions = ref([])
const submitting = ref(false)

const showAdd = ref(false)
const showRoles = ref(false)
const showInfo = ref(false)
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
  await loadData()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
