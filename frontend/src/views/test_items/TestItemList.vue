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
          <el-option label="凝血" value="凝血" />
          <el-option label="其他" value="其他" />
        </el-select>
      </div>
      <el-button v-if="auth.canWrite('test-items')" type="primary" :icon="Plus" size="large" @click="onAdd">新增项目</el-button>
      <el-button v-if="auth.canWrite('test-items')" :icon="Upload" size="large" @click="onPickFile">批量导入</el-button>
      <el-dropdown size="large" split-button type="success" @click="onExport" @command="onExportCommand">
        <el-icon style="margin-right:4px"><Download /></el-icon>导出汇总清单
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="filtered" :disabled="!hasActiveFilter">
              导出当前筛选{{ hasActiveFilter ? `（${total} 条）` : '' }}
            </el-dropdown-item>
            <el-dropdown-item command="all">导出全部项目</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <input ref="fileInput" type="file" accept=".xlsx" style="display:none" @change="onImportFile" />
    </div>

    <div class="stats-bar" v-if="stats">
      <div class="stats-head">
        <span class="stats-title">统计分类</span>
        <span class="stats-total">共 {{ stats.total }} 个项目</span>
        <el-button class="fold-btn" text size="small" :icon="statsCollapsed ? ArrowRight : ArrowDown" @click="statsCollapsed = !statsCollapsed">
          {{ statsCollapsed ? '展开' : '收起' }}
        </el-button>
      </div>
      <div v-show="!statsCollapsed">
        <div class="stats-group">
          <span class="stats-label">按类别：</span>
          <el-tag
            v-for="(cnt, cat) in stats.category_counts"
            :key="'cat-' + cat"
            :type="cat === '生化' ? 'success' : cat === '免疫' ? 'primary' : cat === '凝血' ? 'warning' : 'info'"
            class="stat-tag"
            :effect="query.category === cat ? 'dark' : 'plain'"
            @click="applyCategory(cat)"
          >{{ cat }} ({{ cnt }})</el-tag>
        </div>
        <div class="stats-group">
          <span class="stats-label">按品牌：</span>
          <el-tag
            v-for="(cnt, brand) in stats.brand_counts"
            :key="'brand-' + brand"
            size="small"
            :type="brand === '未标识' ? 'info' : 'warning'"
            class="stat-tag"
            :effect="query.brand === brand ? 'dark' : 'plain'"
            @click="applyBrand(brand)"
          >{{ brand }} ({{ cnt }})</el-tag>
        </div>
        <div class="stats-group">
          <span class="stats-label">按仪器：</span>
          <el-tag
            v-for="(cnt, inst) in stats.instrument_counts"
            :key="'inst-' + inst"
            size="small"
            :type="inst === '未设置' ? 'info' : 'danger'"
            class="stat-tag"
            :effect="query.instrument === inst ? 'dark' : 'plain'"
            :disabled="inst === '未设置'"
            @click="inst === '未设置' ? null : applyInstrument(inst)"
          >{{ inst }} ({{ cnt }})</el-tag>
        </div>
      </div>
    </div>

    <div v-if="query.category || query.brand || query.keyword" class="active-filters">
      <span class="active-filters-label">当前筛选：</span>
      <el-tag v-if="query.category" closable effect="light" :type="categoryType(query.category)" @close="clearFilter('category')">
        类别：{{ query.category }}
      </el-tag>
      <el-tag v-if="query.brand" closable effect="light" type="warning" @close="clearFilter('brand')">
        品牌：{{ query.brand }}
      </el-tag>
      <el-tag v-if="query.instrument" closable effect="light" type="danger" @close="clearFilter('instrument')">
        仪器：{{ query.instrument }}
      </el-tag>
      <el-tag v-if="query.keyword" closable effect="light" type="info" @close="clearFilter('keyword')">
        关键词：{{ query.keyword }}
      </el-tag>
      <el-button text type="primary" size="small" @click="clearAllFilters">清除全部</el-button>
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
            <el-tag v-if="eqaOrgs(row).length" type="success" effect="dark" class="eqa-badge" title="该项目参加室间质评">
              <el-icon class="eqa-ico"><Medal /></el-icon>室间质评（{{ eqaOrgs(row).join('/') }}）
            </el-tag>
            <el-button v-if="rowManuals(row).length" text type="primary" :icon="Document" @click="openManuals(row)" title="查看项目说明书（按品牌）">
              项目说明书<span v-if="rowManuals(row).length > 1">（{{ rowManuals(row).length }}）</span>
            </el-button>
            <el-button v-if="auth.canWrite('test-items')" text :icon="Edit" @click="onEdit(row)">编辑</el-button>
            <el-button v-if="auth.canWrite('test-items')" text type="danger" :icon="Delete" @click="onDelete(row)">删除</el-button>
          </div>
        </div>

        <div class="tag-row">
          <el-tag v-if="row.aliases" size="small" type="info" effect="plain" class="alias-tag"><span v-html="highlight(row.aliases)"></span></el-tag>
          <el-tag v-if="row.instrument" size="small" effect="plain"><span v-html="highlight(row.instrument)"></span></el-tag>
          <el-tag v-if="row.instrument_group" size="small" type="success" effect="plain"><span v-html="highlight(row.instrument_group)"></span></el-tag>
          <el-tag v-if="row.method" size="small" type="primary" effect="plain">
            <span class="tag-label">方法</span><span v-html="highlight(row.method)"></span>
          </el-tag>
          <el-tag v-if="extractBrand(row)" size="small" type="warning" effect="plain">
            <span class="tag-label">品牌</span>{{ extractBrand(row) }}
          </el-tag>
        </div>

        <div v-if="linkedInstruments(row).length" class="linked-inst">
          <span class="linked-label">关联仪器档案：</span>
          <el-tag
            v-for="inst in linkedInstruments(row)"
            :key="inst.id"
            size="small"
            type="info"
            effect="plain"
            class="linked-chip"
            title="新标签打开仪器档案"
            @click="goInstrument(inst.id)"
          >
            <el-icon class="linked-ico"><Link /></el-icon>
            {{ inst.name }}（{{ inst.model }}）
            <span v-if="!inst.has_archive" class="linked-no">· 未建档</span>
          </el-tag>
        </div>

        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">标本类型</div>
            <div class="metric-value" v-html="highlight(row.specimen) || '—'"></div>
          </div>
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
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />

    <el-dialog
      v-model="manualDialog.visible"
      :title="'项目说明书 · ' + manualDialog.project"
      width="82%"
      top="5vh"
      @close="closeManualDialog"
      destroy-on-close
    >
      <div class="manual-layout">
        <div class="manual-list">
          <div
            v-for="m in manualDialog.manuals"
            :key="m.id"
            class="manual-item"
            :class="{ active: manualDialog.current && manualDialog.current.id === m.id }"
            @click="selectManual(m)"
          >
            <div class="manual-item-title">{{ m.title }}</div>
            <div class="manual-item-meta">
              <el-tag v-if="m.brand" size="small" type="warning" effect="plain">{{ m.brand }}</el-tag>
              <el-tag v-if="m.is_pdf" size="small" type="success" effect="plain">PDF</el-tag>
              <el-tag v-else size="small" type="info" effect="plain">{{ (m.ext || '').toUpperCase() }}</el-tag>
            </div>
          </div>
        </div>
        <div class="manual-preview">
          <div v-if="manualDialog.previewLoading" class="manual-loading">
            <el-icon class="is-loading"><Loading /></el-icon> 说明书加载中…
          </div>
          <iframe v-else-if="manualDialog.previewUrl" :src="manualDialog.previewUrl" class="manual-iframe"></iframe>
          <div v-else class="manual-nopreview">
            <el-icon class="nopreview-ico"><Document /></el-icon>
            <p>该说明书为 {{ manualDialog.current && (manualDialog.current.ext || '').toUpperCase() }} 文件，浏览器无法直接预览。</p>
            <el-button type="primary" @click="downloadManual(manualDialog.current)">下载查看</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="downloadManual(manualDialog.current)">下载</el-button>
        <el-button type="primary" @click="closeManualDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete, Warning, Upload, Download, ArrowDown, ArrowRight, Link, Medal, Document, Loading } from '@element-plus/icons-vue'
import EditDialog from '../../components/EditDialog.vue'
import { listTestItems, createTestItem, updateTestItem, deleteTestItem, importTestItems, exportTestItems, getTestItemStats } from '../../api/testItems'
import { getInstrumentFamilyMap } from '../../api/instruments'
import { listEqaAssociations } from '../../api/eqa'
import { listProjectManuals, fetchDocumentBlob, downloadBlob } from '../../api/documents'
import { useAuthStore } from '../../store/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const query = reactive({
  keyword: '',
  category: '',
  brand: '',
  instrument: '',
  page: 1,
  page_size: 10,
})
const statsCollapsed = ref(false)
const items = ref([])
const total = ref(0)
const loading = ref(false)

// 项目「使用仪器」总型号 → 对应仪器档案清单（一对多），用于卡片上跳转
const familyMap = ref({})

// 项目库 × 室间质评 关联（id → {has_wjw, has_bj, ...}），用于卡片标识
const eqaMap = ref({})

// 项目库 × 项目说明书 关联（linked_project 名 → [manuals]），用于卡片预览
const manualMap = ref({})
const manualDialog = reactive({
  visible: false,
  project: '',
  manuals: [],
  current: null,
  previewUrl: '',
  previewLoading: false,
})

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const fileInput = ref(null)

const fields = [
  { prop: 'code', label: '项目编号' },
  { prop: 'name', label: '项目名称' },
  { prop: 'aliases', label: '别名' },
  { prop: 'category', label: '类别', type: 'select', options: [
    { label: '生化', value: '生化' },
    { label: '免疫', value: '免疫' },
    { label: '凝血', value: '凝血' },
    { label: '其他', value: '其他' },
  ] },
  { prop: 'specimen', label: '标本类型', type: 'select', options: [
    { label: '血清', value: '血清' },
    { label: '血浆', value: '血浆' },
    { label: '全血', value: '全血' },
    { label: '尿液', value: '尿液' },
    { label: '脑脊液', value: '脑脊液' },
    { label: '胸腹水', value: '胸腹水' },
    { label: '其他', value: '其他' },
  ] },
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

const rules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

const emptyForm = () => ({
  code: '', name: '', aliases: '', category: '', specimen: '', method: '',
  unit: '', reference: '', fee: '', instrument: '', instrument_group: '',
  linear_range: '', dilution_fold: '', reportable_range: '', diluent: '',
  calibrator: '', traceability: '', last_update: '',
  interference_hemolysis: '', interference_bilirubin: '', interference_lipemia: '',
})
const form = reactive(emptyForm())

onMounted(() => {
  // 从仪器档案「对应项目」点击跳转而来：?q=项目名 时自动按关键词搜索定位
  const q = route.query.q
  if (q) query.keyword = String(q)
  fetchFamilyMap()
  fetchEqaAssociations()
  fetchProjectManuals()
  fetchStats()
  onSearch()
})

// ---- 项目 × 室间质评 关联（用于卡片上显示「室间质评（卫健委/北京市）」标识）----
async function fetchEqaAssociations() {
  try {
    const list = await listEqaAssociations({})
    const m = {}
    for (const a of list) m[a.id] = a
    eqaMap.value = m
  } catch (e) {
    eqaMap.value = {}
  }
}
function eqaOrgs(row) {
  const a = eqaMap.value[row.id]
  if (!a) return []
  const orgs = []
  if (a.has_wjw) orgs.push('卫健委')
  if (a.has_bj) orgs.push('北京市')
  return orgs
}

// ---- 项目 × 项目说明书 关联（卡片点击预览 PDF）----
async function fetchProjectManuals() {
  try {
    const list = await listProjectManuals()
    const m = {}
    for (const d of list) {
      if (!d.linked_project) continue
      ;(m[d.linked_project] = m[d.linked_project] || []).push(d)
    }
    manualMap.value = m
  } catch (e) {
    manualMap.value = {}
  }
}
function rowManuals(row) {
  if (!row) return []
  const seen = new Set()
  const out = []
  const push = (key) => {
    const arr = manualMap.value[key]
    if (!arr) return
    for (const x of arr) {
      if (!seen.has(x.id)) { seen.add(x.id); out.push(x) }
    }
  }
  push(row.name)
  if (row.aliases) {
    for (const a of String(row.aliases).replace('，', ',').split(',')) {
      const key = a.trim()
      if (key) push(key)
    }
  }
  return out
}
function openManuals(row) {
  const ms = rowManuals(row)
  if (!ms.length) return
  manualDialog.project = row.name
  manualDialog.manuals = ms
  manualDialog.visible = true
  manualDialog.current = null
  manualDialog.previewUrl = ''
  selectManual(ms[0])
}
async function selectManual(m) {
  manualDialog.current = m
  if (manualDialog.previewUrl) {
    URL.revokeObjectURL(manualDialog.previewUrl)
    manualDialog.previewUrl = ''
  }
  if (!m.is_pdf) return  // 非 PDF 由「下载查看」处理
  manualDialog.previewLoading = true
  try {
    const blob = await fetchDocumentBlob(m.id, 'preview')
    manualDialog.previewUrl = URL.createObjectURL(blob)
  } catch (e) {
    ElMessage.error('预览加载失败')
  } finally {
    manualDialog.previewLoading = false
  }
}
function closeManualDialog() {
  manualDialog.visible = false
  if (manualDialog.previewUrl) {
    URL.revokeObjectURL(manualDialog.previewUrl)
    manualDialog.previewUrl = ''
  }
}
function downloadManual(m) {
  if (!m) return
  fetchDocumentBlob(m.id, 'download')
    .then((blob) => downloadBlob(blob, `${m.title}${m.ext ? '.' + m.ext : ''}`))
}

// ---- 项目仪器 → 仪器档案 映射（总型号一对多）----
async function fetchFamilyMap() {
  try {
    familyMap.value = await getInstrumentFamilyMap()
  } catch (e) {
    familyMap.value = {}
  }
}
function linkedInstruments(row) {
  if (!row) return []
  const out = []
  const seen = new Set()
  const push = (list) => {
    if (!list) return
    for (const inst of list) {
      if (!seen.has(inst.id)) {
        seen.add(inst.id)
        out.push(inst)
      }
    }
  }
  // 1) 精确关联：优先按「仪器组」中以 '/' 分隔的 token 逐一匹配
  //    （含 急诊 / 唐筛 等，已在关联表映射为具体仪器：DXI800急 / DXI800唐）
  const grp = (row.instrument_group || '').trim()
  if (grp) {
    for (const tk of grp.split('/').map((t) => t.trim()).filter(Boolean)) {
      push(familyMap.value[tk])
    }
  }
  // 2) 仪器组为空或未解析到任何仪器时，回退到「总型号」(instrument) 关联
  if (out.length === 0 && row.instrument) {
    push(familyMap.value[row.instrument])
  }
  return out
}
function goInstrument(id) {
  // 新标签打开仪器档案页，保持当前项目查询页不丢失
  const resolved = router.resolve({ path: '/instruments', query: { focus: id } })
  window.open(resolved.href, '_blank')
}
// ---- 品牌识别（与后端 core.brand 关键词保持一致）----
const BRAND_KEYWORDS = ['贝克曼', '罗氏', '安图', '沃芬', '沃文特', '柏定', '柏荣', '迈瑞', '西门子', '雅培', '东芝', '日立', '优利特', '迪瑞', '利德曼', '九强', '美康', '透景', '科美', '基蛋', '奥森', '积水']
function extractBrand(row) {
  if (!row) return ''
  if (row.brand) return row.brand
  if (!row.calibrator) return ''
  for (const kw of BRAND_KEYWORDS) {
    if (String(row.calibrator).includes(kw)) return kw
  }
  return ''
}

// ---- 统计分类概览 ----
const stats = ref(null)
async function fetchStats() {
  try {
    stats.value = await getTestItemStats()
  } catch (e) {
    stats.value = null
  }
}
function applyCategory(cat) {
  query.category = query.category === cat ? '' : cat
  query.page = 1
  onSearch()
}
function applyBrand(brand) {
  query.brand = query.brand === brand ? '' : brand
  query.page = 1
  onSearch()
}
function applyInstrument(inst) {
  query.instrument = query.instrument === inst ? '' : inst
  query.page = 1
  onSearch()
}
function clearFilter(key) {
  query[key] = ''
  query.page = 1
  onSearch()
}
function clearAllFilters() {
  query.category = ''
  query.brand = ''
  query.instrument = ''
  query.keyword = ''
  query.page = 1
  onSearch()
}
const hasActiveFilter = computed(
  () => !!(query.keyword.trim() || query.category || query.brand || query.instrument)
)

async function doExport({ all = false } = {}) {
  try {
    const params = {}
    let filename = '项目汇总清单.xlsx'
    if (!all && hasActiveFilter.value) {
      if (query.keyword.trim()) params.q = query.keyword.trim()
      if (query.category) params.category = query.category
      if (query.brand) params.brand = query.brand
      if (query.instrument) params.instrument = query.instrument
      const parts = [query.category, query.brand, query.instrument, query.keyword.trim()].filter(Boolean)
      filename = `项目汇总清单_${parts.join('_')}.xlsx`
    }
    const blob = await exportTestItems(params)
    downloadBlob(blob, filename)
    ElMessage.success(all || !hasActiveFilter.value ? '已导出全部项目' : '已导出当前筛选项目')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}
// 主按钮：有筛选则导出当前筛选，无筛选则导出全部
function onExport() {
  doExport({ all: false })
}
// 下拉菜单：filtered=当前筛选 all=全部
function onExportCommand(cmd) {
  doExport({ all: cmd === 'all' })
}

async function onSearch() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
    }
    if (query.keyword.trim()) params.q = query.keyword.trim()
    if (query.category) params.category = query.category
    if (query.brand) params.brand = query.brand
    if (query.instrument) params.instrument = query.instrument
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
  if (cat === '凝血') return 'warning'
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

function onPickFile() {
  fileInput.value?.click()
}
async function onImportFile(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) return
  try {
    const res = await importTestItems(file)
    ElMessage.success(`导入完成：新增 ${res.created} 条，更新 ${res.updated} 条，跳过 ${res.skipped} 条`)
    onSearch()
  } catch (err) {
    const detail = err?.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (err?.message || '未知错误')
    ElMessage.error('导入失败：' + msg)
  } finally {
    e.target.value = ''
  }
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

.stats-bar {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.stats-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 10px;
}
.stats-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a365d;
}
.stats-total {
  font-size: 13px;
  color: #909399;
}
.fold-btn {
  margin-left: auto;
  color: #409eff;
}
.stats-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.stats-group:last-child {
  margin-bottom: 0;
}
.stats-label {
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}
.stat-tag {
  cursor: pointer;
}
.stat-tag:hover {
  opacity: 0.85;
}

.active-filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 16px;
}
.active-filters-label {
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
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

.eqa-badge {
  margin-right: 6px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: linear-gradient(135deg, #1a365d, #2c5282);
  border-color: #1a365d;
  color: #fff;
}
.eqa-ico {
  font-size: 14px;
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

.linked-inst {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 8px 10px;
  background: #f4f8ff;
  border: 1px dashed #c6dbff;
  border-radius: 8px;
}
.linked-label {
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}
.linked-chip {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.linked-chip:hover {
  opacity: 0.82;
  border-color: #409eff;
  color: #409eff;
}
.linked-ico {
  font-size: 12px;
}
.linked-no {
  color: #c0c4cc;
  font-size: 12px;
}

.tag-label {
  margin-right: 4px;
  opacity: 0.8;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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

/* 项目说明书预览对话框 */
.manual-layout {
  display: flex;
  gap: 16px;
  height: 72vh;
  min-height: 420px;
}
.manual-list {
  flex: 0 0 320px;
  max-width: 320px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px;
  background: #f8fafc;
}
.manual-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  margin-bottom: 6px;
  background: #fff;
  transition: all 0.15s;
}
.manual-item:hover {
  border-color: #c6dbff;
}
.manual-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.manual-item-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a365d;
  margin-bottom: 6px;
  line-height: 1.4;
}
.manual-item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.manual-preview {
  flex: 1;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #525659;
  display: flex;
  align-items: center;
  justify-content: center;
}
.manual-iframe {
  width: 100%;
  height: 100%;
  border: 0;
}
.manual-loading {
  color: #fff;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.manual-nopreview {
  color: #fff;
  text-align: center;
  padding: 24px;
}
.nopreview-ico {
  font-size: 48px;
  margin-bottom: 12px;
}
.manual-nopreview p {
  margin: 0 0 16px;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .toolbar > .el-button,
  .toolbar > .el-dropdown {
    width: 100%;
  }
  .search-area {
    max-width: none;
    flex-direction: column !important;
    gap: 10px;
    width: 100%;
  }
  .search-area .el-input,
  .search-area .el-select {
    width: 100% !important;
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
