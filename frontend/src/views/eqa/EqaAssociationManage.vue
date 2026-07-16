<template>
  <div class="page">
    <div class="toolbar">
      <div>
        <h2 class="page-title">项目库与室间质评关联</h2>
        <p class="page-desc">查看项目查询库与室间质评计划的自动匹配关系：哪些项目有质评、属于卫健委还是北京市、哪些尚未覆盖。</p>
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
        placeholder="搜索项目 / 仪器 / EQA 细项..."
        clearable
        size="large"
        style="width: 280px"
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
    </div>

    <el-table v-loading="loading" :data="items" border stripe style="width: 100%">
      <el-table-column type="index" width="60" align="center" label="序号" />
      <el-table-column prop="name" label="项目名称" min-width="220" sortable />
      <el-table-column prop="category" label="类别" width="80" align="center" />
      <el-table-column prop="specimen" label="标本" width="90" align="center" />
      <el-table-column prop="unit" label="单位" width="80" align="center" />
      <el-table-column prop="instrument" label="仪器" min-width="220" show-overflow-tooltip />
      <el-table-column label="卫健委" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_wjw ? 'success' : 'info'">{{ row.has_wjw ? '有' : '无' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="北京市" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_bj ? 'success' : 'info'">{{ row.has_bj ? '有' : '无' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="关联 EQA 细项" min-width="320">
        <template #default="{ row }">
          <template v-if="row.wjw_tokens.length || row.bj_tokens.length">
            <el-tag v-for="t in row.wjw_tokens" :key="'w-' + t" size="small" type="success" effect="plain" class="tag">{{ t }}</el-tag>
            <el-tag v-for="t in row.bj_tokens" :key="'b-' + t" size="small" type="warning" effect="plain" class="tag">{{ t }}</el-tag>
          </template>
          <span v-else class="muted">— 未匹配 —</span>
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

function onExport() {
  if (!items.value.length) {
    ElMessage.warning('当前没有可导出的数据')
    return
  }
  const headers = ['项目名称', '类别', '标本', '单位', '仪器', '品牌', '卫健委', '北京市', '关联EQA细项']
  const rows = items.value.map((r) => [
    r.name,
    r.category,
    r.specimen,
    r.unit,
    r.instrument,
    r.brand,
    r.has_wjw ? '有' : '无',
    r.has_bj ? '有' : '无',
    [...r.wjw_tokens.map((t) => `卫健委:${t}`), ...r.bj_tokens.map((t) => `北京市:${t}`)].join('；'),
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
  max-width: 720px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.stats-bar {
  margin-bottom: 12px;
  color: #606266;
  font-size: 14px;
}
.tag {
  margin: 0 6px 6px 0;
}
.muted {
  color: #c0c4cc;
}
</style>
