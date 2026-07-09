<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索名称 / 编号 / 型号 / 负责人..."
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    >
      <template #row-extra="{ row }">
        <el-button link type="warning" @click="openCalib(row)">校准记录</el-button>
      </template>
    </CrudTable>

    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑仪器' : '新增仪器'"
      :form="form"
      :fields="fields"
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />

    <!-- 校准记录 -->
    <el-dialog v-model="calibOpen" :title="`校准记录 - ${calibInstrument?.name || ''}`" width="720px">
      <el-table :data="calibs" border stripe>
        <el-table-column prop="calibration_date" label="校准日期" width="130" />
        <el-table-column prop="next_due_date" label="下次到期" width="130" />
        <el-table-column prop="result" label="结果" min-width="140" show-overflow-tooltip />
        <el-table-column prop="operator" label="校准人" width="100" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click="delCalib(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider>新增校准记录</el-divider>
      <el-form :model="calibForm" label-width="100px" inline>
        <el-form-item label="校准日期" required>
          <el-date-picker v-model="calibForm.calibration_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="下次到期" required>
          <el-date-picker v-model="calibForm.next_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="校准人">
          <el-input v-model="calibForm.operator" style="width: 140px" />
        </el-form-item>
        <el-form-item label="结果">
          <el-input v-model="calibForm.result" style="width: 240px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calibOpen = false">关闭</el-button>
        <el-button type="primary" :loading="calibSubmitting" @click="addCalib">添加记录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import {
  listInstruments, createInstrument, updateInstrument, deleteInstrument,
  listCalibrations, createCalibration, deleteCalibration,
} from '../../api/instruments'

const crud = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const STATUS_OPTIONS = ['在用', '备用', '维修', '停用'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'name', label: '仪器名称' },
  { prop: 'dept_no', label: '科室编号' },
  { prop: 'model', label: '规格型号' },
  { prop: 'manufacturer', label: '生产厂家' },
  { prop: 'category', label: '类别' },
  { prop: 'serial_no', label: '出厂编号' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'location', label: '存放位置' },
  { prop: 'owner', label: '设备负责人' },
  { prop: 'purchase_date', label: '购入日期', type: 'date' },
  { prop: 'start_date', label: '启用日期', type: 'date' },
]

const rules = {
  name: [{ required: true, message: '请填写仪器名称', trigger: 'blur' }],
}

const columns = [
  { prop: 'name', label: '名称', width: 180 },
  { prop: 'dept_no', label: '科室编号', width: 150 },
  { prop: 'model', label: '型号', width: 130 },
  { prop: 'manufacturer', label: '厂家', width: 130 },
  { prop: 'serial_no', label: '出厂编号', width: 120 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 在用: 'success', 备用: 'info', 维修: 'warning', 停用: 'danger' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
  { prop: 'location', label: '位置', width: 120 },
  { prop: 'owner', label: '负责人', width: 100 },
]

const emptyForm = () => ({
  name: '', dept_no: '', model: '', manufacturer: '', category: '',
  serial_no: '', status: '在用', location: '', owner: '',
  purchase_date: '', start_date: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listInstruments(params)
}
function onAdd() {
  Object.assign(form, emptyForm())
  editingId.value = null
  dialogVisible.value = true
}
function onEdit(row) {
  Object.assign(form, emptyForm(), row)
  editingId.value = row.id
  dialogVisible.value = true
}
async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) {
      await updateInstrument(editingId.value, { ...form })
    } else {
      await createInstrument({ ...form })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await deleteInstrument(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}

// 校准记录
const calibOpen = ref(false)
const calibInstrument = ref(null)
const calibs = ref([])
const calibSubmitting = ref(false)
const calibForm = reactive({ calibration_date: '', next_due_date: '', result: '', operator: '' })

async function openCalib(row) {
  calibInstrument.value = row
  calibOpen.value = true
  await loadCalibs(row.id)
}
async function loadCalibs(id) {
  try {
    calibs.value = await listCalibrations(id)
  } catch (e) {
    calibs.value = []
  }
}
async function addCalib() {
  if (!calibForm.calibration_date || !calibForm.next_due_date) {
    ElMessage.warning('请填写校准日期与下次到期日')
    return
  }
  calibSubmitting.value = true
  try {
    await createCalibration(calibInstrument.value.id, { ...calibForm })
    ElMessage.success('已添加')
    Object.assign(calibForm, { calibration_date: '', next_due_date: '', result: '', operator: '' })
    await loadCalibs(calibInstrument.value.id)
  } finally {
    calibSubmitting.value = false
  }
}
async function delCalib(row) {
  await ElMessageBox.confirm('确认删除该校准记录？', '提示', { type: 'warning' })
  await deleteCalibration(calibInstrument.value.id, row.id)
  ElMessage.success('已删除')
  await loadCalibs(calibInstrument.value.id)
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
