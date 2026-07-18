<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">项目质量要求</h2>
      <p class="sub">汇集 WS/T 403—2024、2025 北京市检验结果互认、2026 年国家卫健委 NCCL EQA 三类质量标准，便于比对与修改。</p>
    </div>

    <el-tabs v-model="activeSource" class="source-tabs" @tab-change="onTabChange">
      <el-tab-pane
        v-for="s in sources"
        :key="s.id"
        :name="s.id"
      >
        <template #label>
          <span class="tab-label">{{ s.name }}</span>
          <el-tag v-if="counts[s.id]" size="small" class="tab-count">{{ counts[s.id] }}</el-tag>
        </template>
      </el-tab-pane>
    </el-tabs>

    <div class="toolbar">
      <el-input
        v-model="searchKey"
        placeholder="搜索项目名 / 分类 / 备注..."
        clearable
        class="search"
        @keyup.enter="refresh"
        @clear="refresh"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
      <el-button
        v-if="auth.canWrite('quality_requirements')"
        type="primary"
        :icon="MagicStick"
        @click="onSeed"
        :loading="seeding"
      >导入默认标准</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
      border
      height="calc(100vh - 340px)"
      :empty-text="emptyText"
    >
      <el-table-column
        v-for="col in activeColumns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :formatter="col.formatter"
        :show-overflow-tooltip="col.tooltip !== false"
      />
      <el-table-column label="操作" width="140" fixed="right" v-if="auth.canWrite('quality_requirements')">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100, 200]"
      layout="total, sizes, prev, pager, next"
      @current-change="refresh"
      @size-change="onSizeChange"
    />

    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑项目质量要求' : '新增项目质量要求'"
      :form="form"
      :fields="formFields"
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, MagicStick } from '@element-plus/icons-vue'
import EditDialog from '../../components/EditDialog.vue'
import {
  listQualityRequirements, createQualityRequirement, updateQualityRequirement, deleteQualityRequirement,
  listQualitySources, seedQualityRequirements,
} from '../../api/qualityRequirements'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()

const sources = ref([])
const activeSource = ref('wst403-2024')
const searchKey = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)
const counts = ref({})
const emptyText = ref('暂无数据')
const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const seeding = ref(false)

const SOURCE_LABEL = {
  'wst403-2024': { cv: '允许不精密度 (CV)', bias: '允许偏倚 (Bias)', tea: '允许总误差 (TEa)', unit: false },
  'bj-hr-2025':  { cv: '允许不精密度', bias: null, tea: 'EQA 评价标准', unit: true },
  'nccl-2026':   { cv: null, bias: null, tea: '可接受范围（TEa）', unit: false },
}

const activeColumns = computed(() => {
  const label = SOURCE_LABEL[activeSource.value] || SOURCE_LABEL['wst403-2024']
  const cols = [
    { prop: 'category', label: activeSource.value === 'nccl-2026' ? '计划号' : '分类/序号', width: 110 },
    { prop: 'item_code', label: '项目代码', width: 130 },
    { prop: 'item_name', label: '项目名称', minWidth: 200 },
  ]
  if (label.cv) cols.push({ prop: 'cv', label: label.cv, minWidth: 180, tooltip: true })
  if (label.bias) cols.push({ prop: 'bias', label: label.bias, minWidth: 130, tooltip: true })
  if (label.tea) cols.push({ prop: 'tea', label: label.tea, minWidth: 200, tooltip: true })
  if (label.unit) cols.push({ prop: 'unit', label: '单位', width: 110 })
  cols.push({ prop: 'remark', label: '备注', minWidth: 160, tooltip: true })
  cols.push({ prop: 'updated_by', label: '最后修改人', width: 110 })
  cols.push({ prop: 'updated_at', label: '最后更新', width: 170,
    formatter: (r) => r.updated_at ? new Date(r.updated_at).toLocaleString('zh-CN') : '-'
  })
  return cols
})

const formFields = computed(() => {
  const label = SOURCE_LABEL[activeSource.value] || SOURCE_LABEL['wst403-2024']
  const fields = [
    { prop: 'item_name', label: '项目名称（必填）' },
    { prop: 'item_code', label: '项目代码' },
    { prop: 'category', label: activeSource.value === 'nccl-2026' ? '计划号' : '分类/序号' },
  ]
  if (label.cv) fields.push({ prop: 'cv', label: label.cv, type: 'textarea', rows: 2 })
  if (label.bias) fields.push({ prop: 'bias', label: label.bias, type: 'textarea', rows: 2 })
  if (label.tea) fields.push({ prop: 'tea', label: label.tea, type: 'textarea', rows: 2 })
  if (label.unit) fields.push({ prop: 'unit', label: '单位' })
  fields.push({ prop: 'remark', label: '备注', type: 'textarea', rows: 2 })
  return fields
})

const rules = {
  item_name: [{ required: true, message: '请填写项目名称', trigger: 'blur' }],
}

const emptyForm = () => ({
  source: activeSource.value,
  category: '',
  item_code: '',
  item_name: '',
  cv: '',
  bias: '',
  tea: '',
  unit: '',
  remark: '',
  updated_by: '',
})

const form = reactive(emptyForm())

async function loadSources() {
  const r = await listQualitySources()
  sources.value = r.items
  // 顺手统计每个 source 的条目数（用分页接口 totals 估算）
  await Promise.all(sources.value.map(async (s) => {
    try {
      const r = await listQualityRequirements({ source: s.id, page: 1, page_size: 1 })
      counts.value[s.id] = r.data.total
    } catch (e) {
      counts.value[s.id] = 0
    }
  }))
}

async function refresh() {
  loading.value = true
  emptyText.value = '加载中...'
  try {
    const params = { source: activeSource.value, page: page.value, page_size: pageSize.value }
    if (searchKey.value.trim()) params.q = searchKey.value.trim()
    const r = await listQualityRequirements(params)
    rows.value = r.data.items
    total.value = r.data.total
    counts.value[activeSource.value] = r.data.total
    emptyText.value = searchKey.value.trim() ? '没有匹配的项目，试试别的关键词' : '该来源下还没有数据，点右上角「导入默认标准」快速灌库'
  } catch (e) {
    rows.value = []
    total.value = 0
    emptyText.value = '加载失败：' + (e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  page.value = 1
  searchKey.value = ''
  refresh()
}

function onSizeChange() {
  page.value = 1
  refresh()
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
    const payload = { ...form, source: activeSource.value, updated_by: auth.user?.username || '' }
    if (editingId.value) {
      await updateQualityRequirement(editingId.value, payload)
    } else {
      await createQualityRequirement(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    refresh()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.item_name}」(${SOURCE_LABEL[row.source]?.cv ? row.source : row.source})？`, '提示', { type: 'warning' })
  await deleteQualityRequirement(row.id)
  ElMessage.success('已删除')
  refresh()
}

async function onSeed() {
  try {
    await ElMessageBox.confirm('将从三类标准（WS/T 403—2024 / 2025 北京互认 / 2026 NCCL）批量追加缺失条目。已存在的不会覆盖。', '导入默认标准', { type: 'info' })
  } catch { return }
  seeding.value = true
  try {
    const r = await seedQualityRequirements()
    ElMessage.success(`已新增 ${r.data.added} 条；已存在 ${r.data.skipped} 条`)
    await loadSources()
    refresh()
  } catch (e) {
    ElMessage.error('灌库失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    seeding.value = false
  }
}

onMounted(async () => {
  await loadSources()
  refresh()
})
</script>

<style scoped>
.page {
  padding: 16px 20px 0 20px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.page-header { margin-bottom: 8px; }
.title { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0 0; color: #64748b; font-size: 13px; }
.source-tabs { margin-bottom: 4px; }
.tab-label { font-weight: 600; }
.tab-count { margin-left: 6px; }
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 8px 0 12px 0;
}
.search { width: 360px; }
.pager {
  margin: 10px 0 16px 0;
  display: flex;
  justify-content: flex-end;
}
:deep(.el-tabs__nav-wrap)::after { background: transparent; }
:deep(.el-tabs__item) { font-size: 15px; }
</style>
