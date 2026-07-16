<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索名称 / 批号 / 厂家 / 供应商..."
      :show-add="auth.canWrite('reagents')"
      :can-write="auth.canWrite('reagents')"
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑试剂' : '新增试剂'"
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
import { listReagents, createReagent, updateReagent, deleteReagent } from '../../api/reagents'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const STATUS_OPTIONS = ['在库', '预警', '过期', '停用'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'name', label: '试剂名称' },
  { prop: 'brand', label: '品牌/厂家' },
  { prop: 'spec', label: '规格' },
  { prop: 'lot_no', label: '批号' },
  { prop: 'quantity', label: '库存数量' },
  { prop: 'unit', label: '单位', placeholder: '盒 / 支 / 瓶' },
  { prop: 'production_date', label: '生产日期', type: 'date' },
  { prop: 'expiry_date', label: '有效期至', type: 'date' },
  { prop: 'in_date', label: '入库日期', type: 'date' },
  { prop: 'supplier', label: '供应商' },
  { prop: 'storage_condition', label: '储存条件', placeholder: '如 2-8℃' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'operator', label: '经手人' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const rules = {
  name: [{ required: true, message: '请填写试剂名称', trigger: 'blur' }],
}

const columns = [
  { prop: 'name', label: '名称', width: 160 },
  { prop: 'brand', label: '厂家', width: 120 },
  { prop: 'spec', label: '规格', width: 110 },
  { prop: 'lot_no', label: '批号', width: 120 },
  { prop: 'quantity', label: '库存', width: 80 },
  { prop: 'unit', label: '单位', width: 70 },
  { prop: 'expiry_date', label: '有效期至', width: 110 },
  { prop: 'supplier', label: '供应商', width: 140 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 在库: 'success', 预警: 'warning', 过期: 'danger', 停用: 'info' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
]

const emptyForm = () => ({
  name: '', brand: '', spec: '', lot_no: '', quantity: '', unit: '',
  production_date: '', expiry_date: '', in_date: '', supplier: '',
  storage_condition: '', status: '在库', operator: '', remark: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listReagents(params)
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
      await updateReagent(editingId.value, { ...form })
    } else {
      await createReagent({ ...form })
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
  await deleteReagent(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
