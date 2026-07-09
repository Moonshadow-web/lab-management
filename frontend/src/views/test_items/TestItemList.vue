<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索项目编号 / 名称 / 方法..."
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    />
    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑项目' : '新增项目'"
      :form="form"
      :fields="fields"
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
import { listTestItems, createTestItem, updateTestItem, deleteTestItem } from '../../api/testItems'

const crud = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const fields = [
  { prop: 'code', label: '项目编号' },
  { prop: 'name', label: '项目名称' },
  { prop: 'aliases', label: '别名' },
  { prop: 'category', label: '类别' },
  { prop: 'specimen', label: '标本类型' },
  { prop: 'method', label: '方法学' },
  { prop: 'unit', label: '单位' },
  { prop: 'reference', label: '参考范围' },
  { prop: 'fee', label: '收费' },
  { prop: 'instrument', label: '使用仪器' },
  { prop: 'instrument_group', label: '仪器组' },
  { prop: 'linear_range', label: '线性范围' },
  { prop: 'dilution_fold', label: '稀释倍数' },
  { prop: 'reportable_range', label: '可报告范围' },
  { prop: 'diluent', label: '稀释液' },
  { prop: 'calibrator', label: '校准品' },
  { prop: 'traceability', label: '溯源性' },
  { prop: 'last_update', label: '最近更新' },
  { prop: 'interference_hemolysis', label: '溶血干扰' },
  { prop: 'interference_bilirubin', label: '胆红素干扰' },
  { prop: 'interference_lipemia', label: '脂血干扰' },
]

const columns = [
  { prop: 'code', label: '编号', width: 110 },
  { prop: 'name', label: '名称', width: 170 },
  { prop: 'aliases', label: '别名', width: 130, tooltip: true },
  { prop: 'category', label: '类别', width: 100 },
  { prop: 'specimen', label: '标本', width: 90 },
  { prop: 'method', label: '方法学', width: 140 },
  { prop: 'unit', label: '单位', width: 70 },
  { prop: 'reference', label: '参考范围', minWidth: 170 },
]

const emptyForm = () => ({
  code: '', name: '', aliases: '', category: '', specimen: '', method: '',
  unit: '', reference: '', fee: '', instrument: '', instrument_group: '',
  linear_range: '', dilution_fold: '', reportable_range: '', diluent: '',
  calibrator: '', traceability: '', last_update: '',
  interference_hemolysis: '', interference_bilirubin: '', interference_lipemia: '',
})

const form = reactive(emptyForm())

function fetch(params) {
  return listTestItems(params)
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
      await updateTestItem(editingId.value, { ...form })
    } else {
      await createTestItem({ ...form })
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
  await deleteTestItem(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
