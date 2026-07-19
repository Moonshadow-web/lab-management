<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">项目质量要求</h2>
      <p class="sub">汇集 WS/T 403—2024、2025 北京市检验结果互认、2026 年国家卫健委 NCCL EQA 三类质量标准，便于比对与修改。</p>
    </div>

    <el-tabs v-model="activeSource" class="source-tabs" @tab-change="onTabChange">
      <!-- 综合比对标签页（最左边） -->
      <el-tab-pane name="matrix">
        <template #label>
          <span class="tab-label">综合比对</span>
          <el-tag size="small" type="success" class="tab-count">项目库</el-tag>
        </template>
      </el-tab-pane>
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

    <!-- 综合比对视图 -->
    <div v-if="activeSource === 'matrix'" class="matrix-view">
      <div class="toolbar">
        <el-input
          v-model="matrixSearch"
          placeholder="搜索项目名称 / 项目代码 / 别名..."
          clearable
          class="search"
          @keyup.enter="loadMatrix"
          @clear="loadMatrix"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button :icon="Refresh" @click="loadMatrix">刷新</el-button>
      </div>

      <el-table
        v-loading="matrixLoading"
        :data="matrixRows"
        stripe
        border
        height="calc(100vh - 340px)"
        :empty-text="matrixEmptyText"
        style="width: 100%"
      >
        <el-table-column prop="item_name" label="项目名称" min-width="180" fixed="left" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="item-name-cell">{{ row.item_name }}</span>
            <span v-if="row.item_code" class="item-code-sub">{{ row.item_code }}</span>
            <el-tag v-if="row.mentioned_count === 0" size="small" type="info" effect="plain" class="unrecorded-tag">未收录</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="90" />
        <el-table-column prop="specimen" label="标本" width="80" />

        <!-- 行标 WS/T 403 -->
        <el-table-column label="行标 (WS/T 403)" align="center" min-width="280">
          <el-table-column prop="wst403-2024.cv" label="CV%" width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['wst403-2024']?.cv)">{{ row['wst403-2024']?.cv || '–' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="wst403-2024.bias" label="Bias%" width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['wst403-2024']?.bias)">{{ row['wst403-2024']?.bias || '–' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="wst403-2024.tea" label="TEa%" width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['wst403-2024']?.tea)">{{ row['wst403-2024']?.tea || '–' }}</span>
            </template>
          </el-table-column>
        </el-table-column>

        <!-- 北京市互认 -->
        <el-table-column label="北京市互认 (2025)" align="center" min-width="240">
          <el-table-column prop="bj-hr-2025.cv" label="CV%" width="110" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['bj-hr-2025']?.cv)">{{ row['bj-hr-2025']?.cv || '–' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="bj-hr-2025.tea" label="EQA标准" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['bj-hr-2025']?.tea)">{{ row['bj-hr-2025']?.tea || '–' }}</span>
            </template>
          </el-table-column>
        </el-table-column>

        <!-- 卫健委 EQA -->
        <el-table-column label="卫健委 EQA (2026)" align="center" min-width="200">
          <el-table-column prop="nccl-2026.tea" label="可接受范围(TEa)" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="qrCellClass(row['nccl-2026']?.tea)">{{ row['nccl-2026']?.tea || '–' }}</span>
            </template>
          </el-table-column>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        v-model:current-page="matrixPage"
        v-model:page-size="matrixPageSize"
        :total="matrixTotal"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadMatrix"
        @size-change="onMatrixSizeChange"
      />
    </div>

    <!-- 原有各源独立列表视图 -->
    <div v-else class="source-view">
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, MagicStick } from '@element-plus/icons-vue'
import EditDialog from '../../components/EditDialog.vue'
import {
  listQualityRequirements, createQualityRequirement, updateQualityRequirement, deleteQualityRequirement,
  listQualitySources, seedQualityRequirements, getQualityMatrix,
} from '../../api/qualityRequirements'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()

// ── 标签页 ──
const sources = ref([])
// activeSource='matrix' 时显示综合视图；否则为各源 ID
const activeSource = ref('matrix')

// ── 原有各源列表状态 ──
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

// ── 综合矩阵状态 ──
const matrixRows = ref([])
const matrixTotal = ref(0)
const matrixPage = ref(1)
const matrixPageSize = ref(50)
const matrixLoading = ref(false)
const matrixSearch = ref('')
const matrixEmptyText = ref('加载中...')

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

/** 矩阵单元格样式：有值深色、空值灰色 */
function qrCellClass(val) {
  if (!val || val === '') return 'qr-empty'
  return 'qr-filled'
}

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

// ── 综合矩阵加载 ──
async function loadMatrix() {
  matrixLoading.value = true
  matrixEmptyText.value = '加载中...'
  try {
    const params = {
      page: matrixPage.value,
      page_size: matrixPageSize.value,
    }
    if (matrixSearch.value.trim()) params.q = matrixSearch.value.trim()
    const r = await getQualityMatrix(params)
    matrixRows.value = r.items
    matrixTotal.value = r.total
    matrixEmptyText.value = matrixSearch.value.trim()
      ? '没有匹配的项目，试试别的关键词'
      : '暂无数据，请先在各标签页导入默认标准'
  } catch (e) {
    matrixRows.value = []
    matrixTotal.value = 0
    matrixEmptyText.value = '加载失败：' + (e?.response?.data?.detail || e.message)
  } finally {
    matrixLoading.value = false
  }
}

function onMatrixSizeChange() {
  matrixPage.value = 1
  loadMatrix()
}

// ── 各源列表加载 ──
async function loadSources() {
  const r = await listQualitySources()
  sources.value = r.items
  await Promise.all(sources.value.map(async (s) => {
    try {
      const r = await listQualityRequirements({ source: s.id, page: 1, page_size: 1 })
      counts.value[s.id] = r.total
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
    rows.value = r.items
    total.value = r.total
    counts.value[activeSource.value] = r.total
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
  if (activeSource.value === 'matrix') {
    loadMatrix()
  } else {
    page.value = 1
    searchKey.value = ''
    refresh()
  }
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
    ElMessage.success(`已新增 ${r.added} 条；已存在 ${r.skipped} 条`)
    await loadSources()
    // 如果当前在综合页也刷新一下
    if (activeSource.value === 'matrix') loadMatrix()
    else refresh()
  } catch (e) {
    ElMessage.error('灌库失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    seeding.value = false
  }
}

onMounted(async () => {
  await loadSources()
  // 默认进入综合比对页
  if (activeSource.value === 'matrix') {
    loadMatrix()
  } else {
    refresh()
  }
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

/* ── 综合矩阵视图样式 ── */
.matrix-view, .source-view { }

.item-name-cell { font-weight: 600; color: #1e293b; }
.item-code-sub { display: block; font-size: 11px; color: #94a3b8; margin-top: 2px; font-weight: 400; }
.unrecorded-tag { margin-left: 6px; vertical-align: middle; }
.qr-filled { color: #0f766e; font-weight: 500; }
.qr-empty { color: #cbd5e1; }
</style>
