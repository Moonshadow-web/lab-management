<template>
  <div class="vpa-page">
    <div class="vpa-toolbar">
      <el-input v-model="keyword" placeholder="按项目名搜索（如：ALT、ALP）" clearable style="width:280px" @input="reload" />
      <el-button @click="reload">刷新</el-button>
      <span class="vpa-count">共 {{ rows.length }} 个项目 / {{ totalRecords }} 次验证</span>
    </div>

    <el-table :data="rows" v-loading="loading" border stripe row-key="project_name" :default-expand-all="false">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="vpa-detail">
            <div class="vpa-detail-title">最近一次验证结论（报告 #{{ row.latest_id }}）</div>
            <el-table :data="row.latest_items_summary" border size="small" empty-text="本次验证未记录结论">
              <el-table-column label="验证项目" width="120">
                <template #default="{ row: r }">
                  <el-tag size="small">{{ ITEM_LABEL[r.key] || r.key }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="验证结果" min-width="220" prop="result" />
              <el-table-column label="结论" width="100" align="center">
                <template #default="{ row: r }">
                  <el-tag :type="r.conclusion === '无' ? 'info' : ((r.conclusion || '').includes('符合') ? 'success' : 'danger')" size="small">
                    {{ r.conclusion || '—' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <!-- 总结论已彻底移除（不再展示） -->

            <div class="vpa-detail-title" style="margin-top:14px">历史验证记录（{{ row.history_count }} 次）</div>
            <el-table :data="row.all_records" border size="small">
              <el-table-column label="#" width="60" type="index" align="center" />
              <el-table-column label="记录ID" prop="id" width="80" />
              <el-table-column label="验证日期" prop="verify_date" width="120" />
              <el-table-column label="仪器" min-width="140">
                <template #default="{ row: r }">{{ r.instrument_model }} {{ r.instrument_no }}</template>
              </el-table-column>
              <el-table-column label="试剂" prop="reagent" min-width="120" show-overflow-tooltip />
              <el-table-column label="类型" width="70" align="center">
                <template #default="{ row: r }">
                  <el-tag :type="r.report_type === 'qualitative' ? 'warning' : 'primary'" size="small">
                    {{ r.report_type === 'qualitative' ? '定性' : '定量' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="验证项" min-width="200">
                <template #default="{ row: r }">
                  <el-tag v-for="k in r.verify_items" :key="k" size="small" style="margin:1px">
                    {{ ITEM_LABEL[k] || k }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160" align="center" fixed="right">
                <template #default="{ row: r }">
                  <el-button size="small" type="success" plain @click="download(r.id)">下载</el-button>
                  <el-button size="small" type="primary" plain @click="gotoRecord(r.id)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="项目名称" min-width="200" prop="project_name" show-overflow-tooltip />
      <el-table-column label="最近验证" width="120" prop="latest_date" />
      <el-table-column label="仪器" min-width="140">
        <template #default="{ row }">{{ row.latest_instrument || '—' }}</template>
      </el-table-column>
      <el-table-column label="试剂" min-width="120">
        <template #default="{ row }">{{ row.latest_reagent || '—' }}</template>
      </el-table-column>
      <el-table-column label="类型" width="70" align="center">
        <template #default="{ row }">
          <el-tag :type="row.latest_report_type === 'qualitative' ? 'warning' : 'primary'" size="small">
            {{ row.latest_report_type === 'qualitative' ? '定性' : '定量' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="验证项" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="k in row.verify_items" :key="k" size="small" type="info" style="margin:1px">
            {{ ITEM_LABEL[k] || k }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="历史" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.history_count > 1 ? 'warning' : 'info'" size="small">{{ row.history_count }}次</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listVerificationReports, downloadVerificationReport } from '../../api/verificationReports'
import request from '../../utils/request'

const ITEM_LABEL = {
  precision: '精密度', trueness: '正确度', linearity: '线性范围',
  reportable: '可报告范围', reference: '参考范围', specificity: '分析特异性',
  conformity: '方法符合率', lod: '方法检出限',
}

const keyword = ref('')
const rows = ref([])
const loading = ref(false)
const totalRecords = computed(() => rows.value.reduce((s, r) => s + r.history_count, 0))

async function reload() {
  loading.value = true
  try {
    const data = await request.get('/api/v1/project-verification-archive/list-by-project', { params: { keyword: keyword.value } })
    rows.value = data || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally { loading.value = false }
}

async function download(id) {
  try {
    const blob = await downloadVerificationReport(id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `verification_${id}.xlsx`; a.click()
    URL.revokeObjectURL(url)
  } catch { ElMessage.error('下载失败') }
}

function gotoRecord(id) {
  // 跳转到「性能验证记录」tab — 简单起见滚动到顶部
  ElMessage.info(`记录 #${id} 详情请在「性能验证记录」tab 查看`)
}

onMounted(reload)
</script>

<style scoped>
.vpa-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.vpa-count { color: #909399; font-size: 13px; }
.vpa-detail { padding: 10px 18px; background: #fafbfc; border-radius: 6px; }
.vpa-detail-title { font-size: 14px; font-weight: 600; color: #303133; margin: 6px 0 8px; border-left: 3px solid #409eff; padding-left: 8px; }
.vpa-summary-note { margin-top: 10px; padding: 8px 12px; background: #ecf5ff; border-radius: 4px; font-size: 13px; }
</style>
