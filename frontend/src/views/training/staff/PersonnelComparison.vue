<template>
  <div class="personnel-comparison">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索项目/方法/试剂"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    />
    <el-dialog v-model="visible" :title="form.id ? '编辑人员比对' : '新增人员比对'" width="880px" top="3vh">
      <el-form :model="form" label-width="120px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="科室"><el-input v-model="form.department" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="专业组"><el-input v-model="form.specialty_group" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="年份"><el-input v-model="form.year" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="比对项目"><el-input v-model="form.project" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="方法"><el-input v-model="form.method" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="试剂"><el-input v-model="form.reagent" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="试剂批号"><el-input v-model="form.reagent_batch" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="试剂有效期"><el-input v-model="form.reagent_expire" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="检测日期"><el-input v-model="form.test_date" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="样本编号"><el-input v-model="sampleNosText" placeholder="多个以逗号分隔" /></el-form-item>

        <el-divider content-position="left">比对结果</el-divider>
        <div class="plan-toolbar"><el-button :icon="Plus" @click="addRow">加一行</el-button></div>
        <el-table :data="form.results_json" border size="small">
          <el-table-column label="样本" width="120"><template #default="{ row }"><el-input v-model="row.sample" size="small" /></template></el-table-column>
          <el-table-column label="本实验室结果" width="140"><template #default="{ row }"><el-input v-model="row.lab_value" size="small" /></template></el-table-column>
          <el-table-column label="比对实验室结果" width="140"><template #default="{ row }"><el-input v-model="row.compare_value" size="small" /></template></el-table-column>
          <el-table-column label="偏倚" width="100"><template #default="{ row }"><el-input v-model="row.bias" size="small" /></template></el-table-column>
          <el-table-column label="结论" min-width="120"><template #default="{ row }"><el-input v-model="row.conclusion" size="small" placeholder="可接受/不可接受" /></template></el-table-column>
          <el-table-column label="" width="50" align="center"><template #default="{ row }"><el-button link type="danger" :icon="Delete" @click="removeRow(row)" /></template></el-table-column>
        </el-table>

        <el-row :gutter="12" style="margin-top:12px">
          <el-col :span="8"><el-form-item label="一致性结论">
            <el-select v-model="form.concordance" style="width:100%"><el-option label="可接受" value="可接受" /><el-option label="不可接受" value="不可接受" /></el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="操作者"><el-input v-model="form.operator" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="审核者"><el-input v-model="form.reviewer" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="结果分析与总结"><el-input v-model="form.summary" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import { listComparison, createComparison, updateComparison, deleteComparison } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'project', label: '比对项目', width: 160 },
  { prop: 'specialty_group', label: '专业组', width: 110 },
  { prop: 'year', label: '年份', width: 90 },
  { prop: 'method', label: '方法', width: 140 },
  { prop: 'concordance', label: '一致性', width: 110 },
]

const visible = ref(false)
const form = ref(blank())
function blank() {
  return { id: null, department: '检验科', specialty_group: '生免组', year: new Date().getFullYear(),
    project: '', method: '', reagent: '', reagent_batch: '', reagent_expire: '', test_date: '',
    sample_nos: [], results_json: [], concordance: '', summary: '', operator: '', reviewer: '' }
}
const sampleNosText = computed({
  get: () => (form.value.sample_nos || []).join('，'),
  set: (v) => { form.value.sample_nos = v ? v.split(/[，,]/).map((s) => s.trim()).filter(Boolean) : [] },
})
function openForm(row) {
  form.value = row ? { ...row, results_json: row.results_json ? [...row.results_json] : [] } : blank()
  visible.value = true
}
function addRow() { form.value.results_json.push({ sample: '', lab_value: '', compare_value: '', bias: '', conclusion: '' }) }
function removeRow(r) { form.value.results_json = form.value.results_json.filter((x) => x !== r) }
async function save() {
  try {
    if (form.value.id) await updateComparison(form.value.id, form.value)
    else await createComparison(form.value)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteComparison(row.id); ElMessage.success('已删除'); tableRef.value?.refresh() } catch (e) {}
}
function fetch(params) { return listComparison(params) }
</script>

<style scoped>
.plan-toolbar { margin-bottom: 8px; }
</style>
