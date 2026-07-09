<template>
  <div class="page">
    <div class="toolbar">
      <div class="search-area">
        <el-input
          v-model="query.keyword"
          placeholder="搜索项目编号 / 名称 / 别名 / 方法..."
          clearable
          size="large"
          @keyup.enter="onSearch"
          @clear="onSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="onSearch">查询</el-button>
          </template>
        </el-input>
        <el-select
          v-model="query.category"
          placeholder="全部分类"
          clearable
          size="large"
          style="width: 140px"
          @change="onSearch"
        >
          <el-option label="生化" value="生化" />
          <el-option label="免疫" value="免疫" />
          <el-option label="其他" value="其他" />
        </el-select>
      </div>
      <el-button type="primary" :icon="Plus" size="large" @click="onAdd">新增项目</el-button>
    </div>

    <div class="result-header">
      <span class="result-title">查询结果</span>
      <span class="result-count">共 {{ total }} 条记录</span>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="items.length === 0" class="empty-wrap">
      <el-empty description="未找到匹配项目" />
    </div>

    <div v-else class="card-list">
      <el-card
        v-for="row in items"
        :key="row.id"
        class="item-card"
        shadow="hover"
      >
        <div class="card-header">
          <div class="title-group">
            <h3 class="item-name" v-html="highlight(row.name) || '—'"></h3>
            <el-tag v-if="extractCode(row)" type="warning" effect="light" class="code-tag">
              <span v-html="highlight(extractCode(row))"></span>
            </el-tag>
          </div>
          <div class="header-actions">
            <el-tag v-if="row.category" :type="categoryType(row.category)" effect="plain" class="category-tag">
              <span v-html="highlight(row.category)"></span>
            </el-tag>
            <el-button text :icon="Edit" @click="onEdit(row)">编辑</el-button>
            <el-button text type="danger" :icon="Delete" @click="onDelete(row)">删除</el-button>
          </div>
        </div>

        <div class="tag-row">
          <el-tag v-if="row.aliases" size="small" type="info" effect="plain" class="alias-tag"><span v-html="highlight(row.aliases)"></span></el-tag>
          <el-tag v-if="row.instrument" size="small" effect="plain"><span v-html="highlight(row.instrument)"></span></el-tag>
          <el-tag v-if="row.instrument_group" size="small" type="success" effect="plain"><span v-html="highlight(row.instrument_group)"></span></el-tag>
          <el-tag v-if="row.method" size="small" type="primary" effect="plain">
            <span class="tag-label">方法</span><span v-html="highlight(row.method)"></span>
          </el-tag>
        </div>

        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">单位</div>
            <div class="metric-value" v-html="highlight(row.unit) || '—'"></div>
          </div>
          <div class="metric">
            <div class="metric-label">稀释倍数</div>
            <div class="metric-value" v-html="highlight(row.dilution_fold) || '—'"></div>
          </div>
          <div class="metric">
            <div class="metric-label">稀释液</div>
            <div class="metric-value" v-html="highlight(row.diluent) || '—'"></div>
          </div>
        </div>

        <div class="info-list">
          <div class="info-row">
            <span class="info-label">参考范围</span>
            <span class="info-value reference" v-html="highlight(row.reference) || '—'"></span>
          </div>
          <div class="info-row">
            <span class="info-label">线性范围</span>
            <span class="info-value" v-html="highlight(row.linear_range) || '—'"></span>
          </div>
          <div class="info-row">
            <span class="info-label">可报告范围</span>
            <span class="info-value" v-html="highlight(row.reportable_range) || '—'"></span>
          </div>
          <div class="info-row">
            <span class="info-label">校准品</span>
            <span class="info-value" v-html="highlight(row.calibrator) || '—'"></span>
          </div>
          <div class="info-row">
            <span class="info-label">溯源性</span>
            <span class="info-value trace" v-html="highlight(row.traceability) || '—'"></span>
          </div>
        </div>

        <div v-if="row.interference_hemolysis || row.interference_bilirubin || row.interference_lipemia" class="interference-box">
          <div class="interference-title">
            <el-icon><Warning /></el-icon>
            <span>抗干扰性能</span>
          </div>
          <div class="interference-grid">
            <div v-if="row.interference_hemolysis" class="interference-item">
              <div class="interference-label">
                <span class="dot hemolysis"></span>溶血
              </div>
              <div class="interference-value" v-html="highlight(row.interference_hemolysis)"></div>
            </div>
            <div v-if="row.interference_bilirubin" class="interference-item">
              <div class="interference-label">
                <span class="dot bilirubin"></span>黄疸
              </div>
              <div class="interference-value" v-html="highlight(row.interference_bilirubin)"></div>
            </div>
            <div v-if="row.interference_lipemia" class="interference-item">
              <div class="interference-label">
                <span class="dot lipemia"></span>脂血
              </div>
              <div class="interference-value" v-html="highlight(row.interference_lipemia)"></div>
            </div>
          </div>
        </div>

        <div class="card-footer">
          <span v-if="row.specimen" class="specimen">标本：<span v-html="highlight(row.specimen)"></span></span>
          <span v-if="row.last_update" class="update-time">更新于：{{ row.last_update }}</span>
        </div>
      </el-card>
    </div>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @size-change="onSearch"
        @current-change="onSearch"
      />
    </div>

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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete, Warning } from '@element-plus/icons-vue'
import EditDialog from '../../components/EditDialog.vue'
import { listTestItems, createTestItem, updateTestItem, deleteTestItem } from '../../api/testItems'

const query = reactive({
  keyword: '',
  category: '',
  page: 1,
  page_size: 10,
})
const items = ref([])
const total = ref(0)
const loading = ref(false)

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

const emptyForm = () => ({
  code: '', name: '', aliases: '', category: '', specimen: '', method: '',
  unit: '', reference: '', fee: '', instrument: '', instrument_group: '',
  linear_range: '', dilution_fold: '', reportable_range: '', diluent: '',
  calibrator: '', traceability: '', last_update: '',
  interference_hemolysis: '', interference_bilirubin: '', interference_lipemia: '',
})
const form = reactive(emptyForm())

onMounted(() => {
  onSearch()
})

async function onSearch() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
    }
    if (query.keyword.trim()) params.q = query.keyword.trim()
    if (query.category) params.category = query.category
    const res = await listTestItems(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function extractCode(row) {
  if (!row.code) return ''
  // code 形如 "ALT / GPT / Alanine / Aminotransferase" 或 "ALT"
  const first = row.code.split('/')[0].trim()
  return first
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
function highlight(text) {
  const kw = query.keyword.trim()
  const safe = escapeHtml(text)
  if (!kw) return safe
  const kwSafe = escapeHtml(kw)
  const re = new RegExp('(' + escapeRegExp(kwSafe) + ')', 'gi')
  return safe.replace(re, '<mark class="hl">$1</mark>')
}
function categoryType(cat) {
  if (cat === '生化') return 'success'
  if (cat === '免疫') return 'primary'
  return 'info'
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
    onSearch()
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
  onSearch()
}
</script>

<style scoped>
.page {
  height: 100%;
  overflow-y: auto;
  padding: 16px 20px 24px;
  background: #f5f7fa;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.search-area {
  display: flex;
  gap: 12px;
  flex: 1;
  max-width: 700px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a365d;
}

.result-count {
  color: #909399;
  font-size: 14px;
}

.loading-wrap,
.empty-wrap {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.item-card {
  border-radius: 10px;
  border-left: 4px solid #409eff;
}

.item-card :deep(.el-card__body) {
  padding: 18px 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.item-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a365d;
}

.code-tag {
  font-size: 14px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tag {
  margin-right: 6px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.alias-tag {
  color: #e6a23c;
  border-color: #f5d8a8;
  background: #fdf6ec;
}

.tag-label {
  margin-right: 4px;
  opacity: 0.8;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}

.metric {
  min-width: 0;
}

.metric-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 15px;
  font-weight: 600;
  color: #1a365d;
  word-break: break-all;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.info-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.info-label {
  width: 80px;
  flex-shrink: 0;
  font-size: 14px;
  color: #606266;
}

.info-value {
  flex: 1;
  font-size: 14px;
  color: #303133;
  word-break: break-all;
}

.info-value.reference {
  color: #409eff;
  font-weight: 500;
}

.info-value.trace {
  font-style: italic;
  color: #606266;
}

.interference-box {
  background: #f0f9ff;
  border: 1px solid #d6eeff;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}

.interference-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 10px;
}

.interference-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.interference-item {
  background: #fff;
  border-radius: 6px;
  padding: 10px 12px;
}

.interference-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot.hemolysis {
  background: #f56c6c;
}

.dot.bilirubin {
  background: #e6a23c;
}

.dot.lipemia {
  background: #909399;
}

.interference-value {
  font-size: 13px;
  color: #606266;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #909399;
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
}

.specimen {
  color: #606266;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-bottom: 8px;
}

.item-card :deep(mark.hl) {
  background: #fff3a0;
  color: #c0392b;
  border-radius: 3px;
  padding: 0 2px;
  font-weight: 700;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .search-area {
    max-width: none;
  }
  .metric-grid,
  .interference-grid {
    grid-template-columns: 1fr;
  }
  .card-header {
    flex-direction: column;
    gap: 8px;
  }
  .header-actions {
    align-self: flex-end;
  }
}
</style>
