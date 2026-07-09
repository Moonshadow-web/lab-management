<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索项目 / 类型 / 仪器 / 操作者..."
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑性能验证' : '新增性能验证'"
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
import { listVerification, createVerification, updateVerification, deleteVerification } from '../../api/verification'

const crud = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const TYPE_OPTIONS = ['精密度', '正确度', '线性范围', '可报告范围', '携带污染', '参考区间', '检出限'].map((v) => ({ label: v, value: v }))
const CONCLUSION_OPTIONS = ['通过', '不通过', '待复核'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'test_item', label: '验证项目' },
  { prop: 'verify_type', label: '验证类型', type: 'select', options: TYPE_OPTIONS },
  { prop: 'instrument', label: '仪器' },
  { prop: 'verify_date', label: '验证日期', type: 'date' },
  { prop: 'criteria', label: '判定标准', placeholder: '如 CV<3%' },
  { prop: 'result', label: '验证结果', type: 'textarea' },
  { prop: 'conclusion', label: '结论', type: 'select', options: CONCLUSION_OPTIONS },
  { prop: 'report_file_path', label: '报告文件路径' },
  { prop: 'operator', label: '操作者' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const rules = {
  test_item: [{ required: true, message: '请填写验证项目', trigger: 'blur' }],
}

const columns = [
  { prop: 'test_item', label: '项目', width: 150 },
  { prop: 'verify_type', label: '验证类型', width: 110 },
  { prop: 'instrument', label: '仪器', width: 120 },
  { prop: 'verify_date', label: '日期', width: 110 },
  { prop: 'criteria', label: '判定标准', minWidth: 130 },
  { prop: 'result', label: '结果', minWidth: 150 },
  {
    prop: 'conclusion', label: '结论', width: 90,
    formatter: (row) => {
      const map = { 通过: 'success', 不通过: 'danger', 待复核: 'warning' }
      const t = map[row.conclusion] || 'info'
      return `<el-tag type="${t}" size="small">${row.conclusion || '-'}</el-tag>`
    },
  },
  { prop: 'operator', label: '操作者', width: 90 },
]

const emptyForm = () => ({
  test_item: '', verify_type: '精密度', instrument: '', verify_date: '',
  criteria: '', result: '', conclusion: '通过', report_file_path: '',
  operator: '', remark: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listVerification(params)
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
      await updateVerification(editingId.value, { ...form })
    } else {
      await createVerification({ ...form })
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
  await ElMessageBox.confirm(`确认删除「${row.test_item} - ${row.verify_type}」？`, '提示', { type: 'warning' })
  await deleteVerification(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
