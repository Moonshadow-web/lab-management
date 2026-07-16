<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索人员 / 主题 / 组织方..."
      :show-add="auth.canWrite('training')"
      :can-write="auth.canWrite('training')"
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑培训记录' : '新增培训记录'"
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
import { listTraining, createTraining, updateTraining, deleteTraining } from '../../api/training'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const CATEGORY_OPTIONS = ['院内培训', '院外培训', '线上课程', '学术会议', '岗位培训'].map((v) => ({ label: v, value: v }))
const STATUS_OPTIONS = ['已完成', '进行中', '未通过'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'person', label: '人员姓名' },
  { prop: 'title', label: '培训主题' },
  { prop: 'category', label: '培训类型', type: 'select', options: CATEGORY_OPTIONS },
  { prop: 'train_date', label: '培训日期', type: 'date' },
  { prop: 'hours', label: '学时' },
  { prop: 'credits', label: '学分' },
  { prop: 'organizer', label: '组织方' },
  { prop: 'certificate_no', label: '证书编号' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const rules = {
  person: [{ required: true, message: '请填写人员姓名', trigger: 'blur' }],
  title: [{ required: true, message: '请填写培训主题', trigger: 'blur' }],
}

const columns = [
  { prop: 'person', label: '人员', width: 100 },
  { prop: 'title', label: '培训主题', minWidth: 200 },
  { prop: 'category', label: '类型', width: 110 },
  { prop: 'train_date', label: '日期', width: 110 },
  { prop: 'hours', label: '学时', width: 70 },
  { prop: 'credits', label: '学分', width: 70 },
  { prop: 'organizer', label: '组织方', width: 140 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 已完成: 'success', 进行中: 'warning', 未通过: 'danger' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
]

const emptyForm = () => ({
  person: '', title: '', category: '院内培训', train_date: '', hours: '',
  credits: '', organizer: '', certificate_no: '', status: '已完成', remark: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listTraining(params)
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
      await updateTraining(editingId.value, { ...form })
    } else {
      await createTraining({ ...form })
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
  await ElMessageBox.confirm(`确认删除「${row.person} - ${row.title}」？`, '提示', { type: 'warning' })
  await deleteTraining(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
