<template>
  <div class="courseware-library">
    <div class="cw-head">
      <div class="cw-title">
        <h3>培训课件库</h3>
        <span class="cw-sub">组内培训 / 科内培训 / 实习讲课的课件，点击即可在线预览或下载</span>
      </div>
      <el-input
        v-model="keyword"
        placeholder="搜索课件名或培训主题"
        clearable
        style="width: 280px"
        @keyup.enter="load"
        @clear="load"
      >
        <template #append><el-button @click="load">搜索</el-button></template>
      </el-input>
    </div>

    <el-radio-group v-model="tag" class="cw-filter" @change="load">
      <el-radio-button value="">全部（{{ total }}）</el-radio-button>
      <el-radio-button v-for="t in TAG_LIST" :key="t" :value="t">
        {{ t }}（{{ counts[t] || 0 }}）
      </el-radio-button>
    </el-radio-group>

    <el-table :data="items" v-loading="loading" border stripe size="small" style="margin-top: 12px">
      <el-table-column label="类别" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.tag)">{{ row.tag }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="session_name" label="培训主题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="original_name" label="课件文件" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <span style="color: #2563eb; cursor: pointer" @click="preview(row)">{{ row.original_name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100" align="center">
        <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="train_time" label="培训时间" width="120" align="center">
        <template #default="{ row }">{{ row.train_time || '—' }}</template>
      </el-table-column>
      <el-table-column label="上传时间" width="160" align="center">
        <template #default="{ row }">{{ (row.uploaded_at || '').slice(0, 10) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="preview(row)">预览</el-button>
          <el-button link type="primary" @click="download(row)">下载</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <div style="padding: 24px; color: #909399">暂无课件</div>
      </template>
    </el-table>

    <div v-if="total > pageSize" style="margin-top: 12px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="load"
      />
    </div>

    <AttachmentPreview
      :visible="previewVisible"
      :file="previewFile"
      :get-url="(id, inline) => eduAttachmentUrl(id, inline)"
      @update:visible="(v) => (previewVisible = v)"
      @download="download"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AttachmentPreview from '../../../components/AttachmentPreview.vue'
import { listCoursewareLibrary, eduAttachmentUrl, downloadEduAttachment } from '../../../api/education'

const TAG_LIST = ['组内培训', '科内培训', '实习讲课']

const items = ref([])
const counts = ref({})
const total = ref(0)
const loading = ref(false)
const tag = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(100)

const previewVisible = ref(false)
const previewFile = ref(null)

function tagType(t) {
  return { 组内培训: 'success', 科内培训: 'warning', 实习讲课: 'info' }[t] || ''
}

function formatSize(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

async function load() {
  loading.value = true
  try {
    const res = await listCoursewareLibrary({
      tag: tag.value,
      q: keyword.value,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.items || []
    total.value = res.total || 0
    counts.value = res.counts || {}
  } finally {
    loading.value = false
  }
}

function preview(row) {
  previewFile.value = row
  previewVisible.value = true
}

async function download(row) {
  const tip = ElMessage({ message: `正在下载：${row.original_name}`, duration: 0, type: 'info' })
  try {
    await downloadEduAttachment(row.id, row.original_name)
    tip.close()
  } catch (e) {
    tip.close()
    ElMessage.error('下载失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(load)
</script>

<style scoped>
.courseware-library {
  padding: 4px 2px 12px;
}
.cw-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.cw-title h3 {
  margin: 0;
  font-size: 16px;
}
.cw-sub {
  color: #909399;
  font-size: 12px;
}
.cw-filter {
  margin-top: 10px;
}
</style>
