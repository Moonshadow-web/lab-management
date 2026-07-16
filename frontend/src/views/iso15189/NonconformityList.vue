<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索标题 / 描述 / 责任人 / 纠正措施..."
      :show-add="auth.canWrite('iso15189')"
      :can-write="auth.canWrite('iso15189')"
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑不符合项' : '新增不符合项'"
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
import { listNC, createNC, updateNC, deleteNC } from '../../api/nonconformity'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const TYPE_OPTIONS = ['体系性', '技术性', '管理性'].map((v) => ({ label: v, value: v }))
const SOURCE_OPTIONS = ['内审', '外审', '日常监督', '客户投诉', '能力验证', '管理评审'].map((v) => ({ label: v, value: v }))
const STATUS_OPTIONS = ['待处理', '整改中', '已关闭', '已验证'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'title', label: '标题' },
  { prop: 'nc_type', label: '类型', type: 'select', options: TYPE_OPTIONS },
  { prop: 'source', label: '来源', type: 'select', options: SOURCE_OPTIONS },
  { prop: 'description', label: '问题描述', type: 'textarea' },
  { prop: 'root_cause', label: '原因分析', type: 'textarea' },
  { prop: 'corrective_action', label: '纠正措施', type: 'textarea' },
  { prop: 'responsible', label: '责任人' },
  { prop: 'found_date', label: '发现日期', type: 'date' },
  { prop: 'due_date', label: '要求完成', type: 'date' },
  { prop: 'close_date', label: '关闭日期', type: 'date' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
]

const rules = {
  title: [{ required: true, message: '请填写标题', trigger: 'blur' }],
}

const columns = [
  { prop: 'title', label: '标题', minWidth: 200 },
  { prop: 'nc_type', label: '类型', width: 90 },
  { prop: 'source', label: '来源', width: 100 },
  { prop: 'responsible', label: '责任人', width: 90 },
  { prop: 'found_date', label: '发现日期', width: 110 },
  { prop: 'due_date', label: '要求完成', width: 110 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 待处理: 'danger', 整改中: 'warning', 已关闭: 'info', 已验证: 'success' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
]

const emptyForm = () => ({
  title: '', nc_type: '技术性', source: '内审', description: '', root_cause: '',
  corrective_action: '', responsible: '', found_date: '', due_date: '',
  close_date: '', status: '待处理',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listNC(params)
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
      await updateNC(editingId.value, { ...form })
    } else {
      await createNC({ ...form })
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
  await ElMessageBox.confirm(`确认删除「${row.title}」？`, '提示', { type: 'warning' })
  await deleteNC(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
