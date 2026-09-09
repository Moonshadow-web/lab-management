<template>
  <div class="post-instrument-map">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <div>
        <h2 class="title" style="margin:0;">岗位仪器匹配</h2>
        <span style="color:#666;font-size:12px;">维护「岗位 → 关键仪器」对应关系（BG-KS-GL-070 仪器使用授权书）；岗前培训考核表选岗位后据此自动带出仪器</span>
      </div>
      <div style="display:flex;gap:8px;">
        <el-button size="small" @click="seedFromMeta" :disabled="!canWrite">一键导入现有映射</el-button>
        <el-button type="primary" size="small" @click="openForm()" :disabled="!canWrite">新增匹配</el-button>
      </div>
    </div>

    <el-table :data="list" border size="small" v-loading="loading">
      <el-table-column prop="post" label="岗位" width="140" />
      <el-table-column prop="instrument_name" label="仪器名称" min-width="200" />
      <el-table-column prop="instrument_code" label="仪器编号" width="180" />
      <el-table-column prop="manager" label="仪器管理者" width="110" />
      <el-table-column label="考核方式" min-width="150">
        <template #default="{ row }"><el-tag v-for="m in row.methods_json" :key="m" size="small" style="margin-right:4px;">{{ m }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="sort_no" label="排序" width="70" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!canWrite" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" :disabled="!canWrite" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑匹配' : '新增匹配'" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="岗位">
          <el-select v-model="form.post" filterable allow-create default-first-option style="width:100%">
            <el-option v-for="p in presetPosts" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="仪器名称"><el-input v-model="form.instrument_name" /></el-form-item>
        <el-form-item label="仪器编号"><el-input v-model="form.instrument_code" placeholder="如 MHZYY-JYK-SM-2010" /></el-form-item>
        <el-form-item label="仪器管理者"><el-input v-model="form.manager" style="width:200px;" /></el-form-item>
        <el-form-item label="考核方式">
          <el-select v-model="methods" multiple style="width:100%"><el-option v-for="m in ALL" :key="m" :label="m" :value="m" /></el-select>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_no" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GL070_POSITIONS } from '../../views/training/staff/gl070Meta'
import { useAuthStore } from '../../store/auth'
import {
  listPostInstrumentMap, createPostInstrumentMap, updatePostInstrumentMap, deletePostInstrumentMap,
} from '../../api/education'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const ALL = ['口头问答', '实操考核', '理论考核']
const presetPosts = GL070_POSITIONS.map((p) => p.name)
const list = ref([])
const loading = ref(false)
const visible = ref(false)
const methods = ref([])
const form = ref(blank())
function blank() { return { id: null, post: '', instrument_name: '', instrument_code: '', manager: '', sort_no: 0, remark: '' } }

async function refresh() {
  loading.value = true
  try {
    const res = await listPostInstrumentMap({ page: 1, page_size: 200 })
    list.value = res.items || []
  } finally { loading.value = false }
}
onMounted(refresh)

function openForm(row) {
  form.value = row ? { ...row } : blank()
  methods.value = row ? [...(row.methods_json || [])] : []
  visible.value = true
}
async function save() {
  if (!form.value.post || !form.value.instrument_name) { ElMessage.error('岗位与仪器名称必填'); return }
  const payload = { ...form.value, methods_json: methods.value }
  try {
    if (payload.id) await updatePostInstrumentMap(payload.id, payload)
    else await createPostInstrumentMap(payload)
    ElMessage.success('已保存'); visible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`删除「${row.post} - ${row.instrument_name}」？`, '提示', { type: 'warning' })
    await deletePostInstrumentMap(row.id); ElMessage.success('已删除'); refresh()
  } catch (e) {}
}
// 一键导入 gl070Meta 现有映射（已含 A6200→SM-2010、DXI800 以库为准、一体机归病房岗）
async function seedFromMeta() {
  try {
    await ElMessageBox.confirm('将把系统内置的岗位-仪器映射导入（已有数据会保留，重复编号跳过）。继续？', '提示', { type: 'warning' })
  } catch (e) { return }
  const exist = new Set((list.value || []).map((x) => x.instrument_code))
  let n = 0
  for (const p of GL070_POSITIONS) {
    let i = 0
    for (const inst of p.instruments) {
      if (exist.has(inst.code)) { i++; continue }
      await createPostInstrumentMap({
        post: p.name, instrument_name: inst.name, instrument_code: inst.code,
        manager: inst.manager || '', methods_json: p.methods || [], sort_no: i++,
      })
      n++
    }
  }
  ElMessage.success(`已导入 ${n} 条`)
  refresh()
}
</script>
