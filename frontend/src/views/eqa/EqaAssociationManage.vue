<template>
  <div class="page">
    <div class="toolbar">
      <div>
        <h2 class="page-title">项目库与质评关联</h2>
        <p class="page-desc">一行看全景：EQA 覆盖情况（卫健委/北京市）+ 三个质量标准的允许误差指标（行标 / 北京互认 / 卫健委 EQA）。</p>
      </div>
      <el-button :icon="Download" size="large" @click="onExport">导出当前筛选</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="query.category" placeholder="全部分类" clearable size="large" @change="onSearch">
        <el-option label="生化" value="生化" />
        <el-option label="免疫" value="免疫" />
        <el-option label="凝血" value="凝血" />
      </el-select>
      <el-select v-model="query.has_eqa" placeholder="全部项目" clearable size="large" @change="onSearch">
        <el-option label="有质评" value="yes" />
        <el-option label="无质评" value="no" />
      </el-select>
      <el-select v-model="query.org" placeholder="全部机构" clearable size="large" @change="onSearch">
        <el-option label="卫健委" value="wjw" />
        <el-option label="北京市" value="bj" />
      </el-select>
      <el-input
        v-model="query.keyword"
        placeholder="搜索项目 / 仪器 / EQA 细项 / 标准要求..."
        clearable
        size="large"
        style="width: 300px"
        @keyup.enter="onSearch"
        @clear="onSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="onSearch" />
        </template>
      </el-input>
    </div>

    <div class="stats-bar" v-if="items.length">
      <span>共 {{ items.length }} 个项目</span>
      <el-divider direction="vertical" />
      <span>有质评：{{ hasEqaCount }} 个</span>
      <el-divider direction="vertical" />
      <span>仅卫健委：{{ onlyWjwCount }} 个</span>
      <el-divider direction="vertical" />
      <span>仅北京市：{{ onlyBjCount }} 个</span>
      <el-divider direction="vertical" />
      <span>两者都有：{{ bothCount }} 个</span>
      <el-divider direction="vertical" />
      <span class="stat-highlight">行标覆盖：{{ wst403Count }} 个</span>
      <el-divider direction="vertical" />
      <span class="stat-highlight">北京互认覆盖：{{ bjHrCount }} 个</span>
      <el-divider direction="vertical" />
      <span class="stat-highlight">卫健委EQA覆盖：{{ ncclCount }} 个</span>
    </div>

    <el-table v-loading="loading" :data="items" border stripe style="width: 100%" :height="tableHeight">
      <el-table-column type="index" width="50" align="center" label="#" fixed="left" />
      <el-table-column prop="name" label="项目名称" min-width="180" sortable fixed="left">
        <template #default="{ row }">
          <span class="item-name">{{ row.name }}</span>
          <span v-if="row.specimen" class="spec-tag">{{ row.specimen }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="category" label="类别" width="70" align="center" />
      <el-table-column prop="unit" label="单位" width="70" align="center" />
      <el-table-column label="卫健委" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_wjw ? 'success' : 'info'" size="small">{{ row.has_wjw ? '✓' : '—' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="北京" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_bj ? 'success' : 'info'" size="small">{{ row.has_bj ? '✓' : '—' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="关联 EQA 细项" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="row.wjw_tokens.length || row.bj_tokens.length">
            <el-tag v-for="t in row.wjw_tokens" :key="'w-' + t" size="small" type="success" effect="plain" class="tag">{{ t }}</el-tag>
            <el-tag v-for="t in row.bj_tokens" :key="'b-' + t" size="small" type="warning" effect="plain" class="tag">{{ t }}</el-tag>
          </template>
          <span v-else class="muted">— 未匹配 —</span>
        </template>
      </el-table-column>
      <!-- ── 质量标准三列 ── -->
      <el-table-column label="行标 (WS/T 403)" min-width="200" align="left">
        <template #default="{ row }">
          <template v-if="row.wst403">
            <div class="qr-cell"><b>CV:</b> <span class="qr-val">{{ row.wst403.cv || '—' }}</span></div>
            <div class="qr-cell"><b>Bias:</b> <span class="qr-val">{{ row.wst403.bias || '—' }}</span></div>
            <div class="qr-cell"><b>TEa:</b> <span class="qr-val tea">{{ row.wst403.tea || '—' }}</span></div>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="北京互认" min-width="200" align="left">
        <template #default="{ row }">
          <template v-if="row.bj_hr">
            <div class="qr-cell"><b>CV:</b> <span class="qr-val">{{ row.bj_hr.cv || '—' }}</span></div>
            <div class="qr-cell"><b>EQA:</b> <span class="qr-val tea">{{ row.bj_hr.tea || '—' }}</span></div>
            <div v-if="row.bj_hr.unit" class="qr-cell unit-sub">{{ row.bj_hr.unit }}</div>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="卫健委 EQA 标准" min-width="200" align="left">
        <template #default="{ row }">
          <template v-if="row.nccl">
            <div class="qr-cell"><b>可接受范围:</b> <span class="qr-val tea">{{ row.nccl.tea || '—' }}</span></div>
            <div v-if="row.nccl.item_name && row.nccl.item_name !== row.name" class="qr-cell source-name">{{ row.nccl.item_name }}</div>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import { listEqaAssociations } from '../../api/eqa'

const items = ref([])
const loading = ref(false)
const query = reactive({ category: '', has_eqa: '', org: '', keyword: '' })

const hasEqaCount = computed(() => items.value.filter((r) => r.has_eqa).length)
const onlyWjwCount = computed(() => items.value.filter((r) => r.has_wjw && !r.has_bj).length)
const onlyBjCount = computed(() => items.value.filter((r) => r.has_bj && !r.has_wjw).length)
const bothCount = computed(() => items.value.filter((r) => r.has_wjw && r.has_bj).length)
const wst403Count = computed(() => items.value.filter((r) => r.wst403).length)
const bjHrCount = computed(() => items.value.filter((r) => r.bj_hr).length)
const ncclCount = computed(() => items.value.filter((r) => r.nccl).length)

// 表格高度自适应
const tableHeight = computed(() => {
  return Math.max(400, window.innerHeight - 320)
})

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (query.category) params.category = query.category
    if (query.has_eqa) params.has_eqa = query.has_eqa
    if (query.org) params.org = query.org
    if (query.keyword) params.keyword = query.keyword
    items.value = await listEqaAssociations(params)
  } catch (e) {
    const detail = e?.response?.data?.detail
    ElMessage.error('加载失败：' + (typeof detail === 'string' ? detail : (e?.message || '未知错误')))
  } finally {
    loading.value = false
  }
}

function onSearch() {
  fetchData()
}

/** 格式化质量要求单源为可读文本 */
function _qrText(qr) {
  if (!qr) return ''
  const parts = []
  if (qr.cv) parts.push('CV:' + qr.cv)
  if (qr.bias) parts.push('Bias:' + qr.bias)
  if (qr.tea) parts.push('TEa:' + qr.tea)
  return parts.join(' | ')
}

function onExport() {
  if (!items.value.length) {
    ElMessage.warning('当前没有可导出的数据')
    return
  }
  const headers = [
    '项目名称', '类别', '标本', '单位',
    '卫健委', '北京市', '关联EQA细项',
    '行标-CV', '行标-Bias', '行标-TEa',
    '北京互认-CV', '北京互认-EQA标准', '北京互认-单位',
    '卫健委EQA-可接受范围', '匹配质量',
  ]
  const rows = items.value.map((r) => [
    r.name,
    r.category,
    r.specimen,
    r.unit,
    r.has_wjw ? '有' : '无',
    r.has_bj ? '有' : '无',
    [...r.wjw_tokens.map((t) => `卫:${t}`), ...r.bj_tokens.map((t) => `北:${t}`)].join('；'),
    r.wst403?.cv || '',
    r.wst403?.bias || '',
    r.wst403?.tea || '',
    r.bj_hr?.cv || '',
    r.bj_hr?.tea || '',
    r.bj_hr?.unit || '',
    r.nccl?.tea || '',
    r.match_score,
  ])
  let csv = '\uFEFF' + headers.join(',') + '\n'
  rows.forEach((r) => {
    csv += r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',') + '\n'
  })
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `项目库与质评关联_${new Date().toLocaleDateString()}.csv`
  link.click()
  ElMessage.success('导出成功')
}
</script>

<style scoped>
.page {
  padding: 16px 20px 24px;
  background: #f5f7fa;
  min-height: 100%;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}
.page-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: #1a365d;
}
.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
  max-width: 780px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  align-items: center;
}
.stats-bar {
  margin-bottom: 10px;
  color: #606266;
  font-size: 13px;
  line-height: 1.8;
}
.stat-highlight { color: #0f766e; font-weight: 600; }
.tag {
  margin: 0 6px 6px 0;
}
.muted { color: #c0c4cc; }

/* 项目名称 */
.item-name { font-weight: 600; color: #1e293b; }
.spec-tag {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 0 4px;
  border-radius: 3px;
  font-weight: 400;
}

/* 质量要求单元格 */
.qr-cell { line-height: 1.6; font-size: 12.5px; white-space: nowrap; }
.qr-cell b { color: #64748b; font-weight: 500; display: inline-block; min-width: 42px; }
.qr-val { color: #334155; font-weight: 500; }
.qr-val.tea { color: #0f766e; font-weight: 600; }
.unit-sub { color: #94a3b8; font-size: 11.5px; }
.source-name { color: #94a3b8; font-size: 11.5px; }
</style>
