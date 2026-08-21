<template>
  <div class="sum-page">
    <!-- 汇总表头信息 -->
    <el-card class="sum-card" shadow="never">
      <div class="sum-head">
        <div>
          <h2 class="sum-title">测量不确定度评定汇总表</h2>
          <div class="sum-meta">
            <span>表格编号：BG-SM-GL-020</span>
            <span>编制日期：{{ today }}</span>
            <span>共 {{ filtered.length }} 项</span>
          </div>
          <div class="sum-note">
            质量目标优先级：WS/T 403-2024（行标） &gt; 2025 北京市互认 &gt; 1/2 × NCCL EQA 允许总误差；U &lt; 质量目标判为符合要求。
          </div>
        </div>
        <div class="sum-actions">
          <el-input
            v-model="kw"
            placeholder="搜索项目名称"
            clearable
            style="width: 220px"
            @input="onSearch"
          />
          <el-button :disabled="!filtered.length" @click="previewSummary">📑 预览汇总表</el-button>
          <el-button type="primary" :disabled="!filtered.length" @click="downloadSummary">⬇️ 下载汇总表 PDF</el-button>
        </div>
      </div>
    </el-card>

    <!-- 汇总列表（所有已生成报告） -->
    <el-table :data="paged" stripe border class="sum-table" v-loading="loading">
      <el-table-column type="index" label="序号" width="60" align="center" :index="indexMethod" />
      <el-table-column prop="project_name" label="项目名称" min-width="160" align="center">
        <template #default="{ row }">
          {{ row.project_name }}
          <el-tag v-if="row.mode === 'multi'" size="small" type="warning" style="margin-left:4px">多系统</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="测量方法" min-width="140" align="center">
        <template #default="{ row }">{{ row.project_method || row.instrument || '-' }}</template>
      </el-table-column>
      <el-table-column label="U(%)" width="90" align="center">
        <template #default="{ row }">{{ fmtPct(row.u_extended) }}</template>
      </el-table-column>
      <el-table-column label="目标偏倚(%)" width="110" align="center">
        <template #default="{ row }">{{ fmtPct(row.target_bias) }}</template>
      </el-table-column>
      <el-table-column prop="target_bias_source" label="目标来源" min-width="160" align="center" show-overflow-tooltip />
      <el-table-column label="判定" width="90" align="center">
        <template #default="{ row }">
          <span :class="row.passed ? 'judge-ok' : 'judge-fail'">{{ row.passed ? '符合' : '未达标' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="eval_date" label="评定日期" width="120" align="center" />
      <el-table-column prop="prepared_by" label="评定人" width="100" align="center" />
      <el-table-column label="操作" width="160" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="previewOne(row)">报告</el-button>
          <el-button size="small" type="success" @click="downloadOne(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="sum-pager" v-if="total > pageSize">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="page"
      />
    </div>

    <!-- 报告预览 -->
    <el-dialog v-model="previewOpen" :title="previewTitle" width="86%" top="3vh">
      <iframe :srcdoc="previewHtml" style="width:100%; height:72vh; border:1px solid #dcdfe6; border-radius:4px"></iframe>
      <template #footer>
        <el-button @click="previewOpen = false">关闭</el-button>
        <el-button type="primary" @click="downloadCurrentHtml">下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'
import {
  todayStr,
  buildSingleReport,
  buildMultiReport,
  buildSummaryReport,
  printOrSavePdf,
  downloadHtml,
} from '../../utils/uncertaintyReport'

const today = ref(todayStr())
const projects = ref([])
const kw = ref('')
const loading = ref(false)
const page = ref(1)
const pageSize = 30

const previewOpen = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')

// 项目搜索：按项目名称模糊过滤
const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return projects.value
  return projects.value.filter((p) => (p.project_name || '').toLowerCase().includes(q))
})

const total = computed(() => filtered.value.length)
const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function indexMethod(i) {
  return (page.value - 1) * pageSize + i + 1
}

function fmtPct(v) {
  const n = Number(v || 0)
  return n ? n.toFixed(2) : '0.00'
}

function onSearch() {
  page.value = 1
}

async function loadProjects() {
  loading.value = true
  try {
    const res = await request.get('/api/v1/uncertainty', { params: { page_size: 300 } })
    projects.value = (res && (res.items || res)) || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message))
  } finally {
    loading.value = false
  }
}

function previewOne(p) {
  previewTitle.value = `测量不确定度评定报告 - ${p.project_name}`
  previewHtml.value = p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p)
  previewOpen.value = true
}

function previewSummary() {
  previewTitle.value = '测量不确定度评定汇总表'
  previewHtml.value = buildSummaryReport(filtered.value)
  previewOpen.value = true
}

function downloadOne(p) {
  printOrSavePdf(
    p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p),
    `测量不确定度评定报告_${p.project_name || '项目'}_${todayStr()}`,
  )
}

function downloadSummary() {
  printOrSavePdf(buildSummaryReport(filtered.value), `测量不确定度评定汇总表_${todayStr()}`)
}

function downloadCurrentHtml() {
  if (previewHtml.value) {
    downloadHtml(previewHtml.value, `${previewTitle.value || '测量不确定度报告'}_${todayStr()}.html`)
  }
}

onMounted(loadProjects)
</script>

<style scoped>
.sum-page { padding: 4px 8px; }
.sum-card { margin-bottom: 14px; }
.sum-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.sum-title { margin: 0 0 6px; font-size: 18px; color: #303133; }
.sum-meta { display: flex; gap: 18px; font-size: 13px; color: #606266; flex-wrap: wrap; }
.sum-note { margin-top: 6px; font-size: 12px; color: #909399; max-width: 760px; line-height: 1.6; }
.sum-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.sum-table { margin-bottom: 12px; }
.judge-ok { color: #303133; }
.judge-fail { color: #303133; }
.sum-pager { display: flex; justify-content: flex-end; }
</style>
