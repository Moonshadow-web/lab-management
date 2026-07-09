<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索项目 / 批号 / 仪器 / 操作者..."
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑质控记录' : '新增质控记录'"
      :form="form"
      :fields="fields"
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import { listQC, createQC, updateQC, deleteQC } from '../../api/qc'

const crud = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const STATUS_OPTIONS = ['在控', '警告', '失控'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'test_item', label: '质控项目' },
  { prop: 'level', label: '质控水平', placeholder: '如 水平1 / 水平2' },
  { prop: 'lot_no', label: '质控品批号' },
  { prop: 'instrument', label: '仪器' },
  { prop: 'target_mean', label: '靶值均值' },
  { prop: 'target_sd', label: '靶值SD' },
  { prop: 'measured_value', label: '测定值' },
  { prop: 'qc_date', label: '质控日期', type: 'date' },
  { prop: 'status', label: '在控状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'rule_violated', label: '违反规则', placeholder: '如 1-2s / 1-3s / 2-2s' },
  { prop: 'operator', label: '操作者' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const rules = {
  test_item: [{ required: true, message: '请填写质控项目', trigger: 'blur' }],
}

const columns = [
  { prop: 'test_item', label: '项目', width: 150 },
  { prop: 'level', label: '水平', width: 90 },
  { prop: 'lot_no', label: '批号', width: 120 },
  { prop: 'instrument', label: '仪器', width: 120 },
  { prop: 'target_mean', label: '靶值', width: 90 },
  { prop: 'target_sd', label: 'SD', width: 80 },
  { prop: 'measured_value', label: '测定值', width: 90 },
  { prop: 'qc_date', label: '日期', width: 110 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 在控: 'success', 警告: 'warning', 失控: 'danger' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
  { prop: 'rule_violated', label: '违反规则', width: 100 },
  { prop: 'operator', label: '操作者', width: 90 },
]

const emptyForm = () => ({
  test_item: '', level: '', lot_no: '', instrument: '', target_mean: '',
  target_sd: '', measured_value: '', qc_date: '', status: '在控',
  rule_violated: '', operator: '', remark: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listQC(params)
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
      await updateQC(editingId.value, { ...form })
    } else {
      await createQC({ ...form })
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
  await ElMessageBox.confirm(`确认删除「${row.test_item}」该条质控记录？`, '提示', { type: 'warning' })
  await deleteQC(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
