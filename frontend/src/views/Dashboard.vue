<template>
  <div class="dashboard">
    <el-row :gutter="16">
      <el-col :span="6">
        <AppCard title="检验项目">
          <div class="stat"><span class="num">{{ stats.testItems }}</span><span class="unit">项</span></div>
          <div class="stat-sub">生化免疫检验项目</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="仪器设备">
          <div class="stat"><span class="num">{{ stats.instruments }}</span><span class="unit">台</span></div>
          <div class="stat-sub">在用 / 停用台账</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="体系文件">
          <div class="stat"><span class="num">{{ stats.documents }}</span><span class="unit">份</span></div>
          <div class="stat-sub">SOP / 记录表格</div>
        </AppCard>
      </el-col>
      <el-col :span="6">
        <AppCard title="待办提醒">
          <div class="stat"><span class="num" :class="{ warn: stats.notifications > 0 }">{{ stats.notifications }}</span><span class="unit">条</span></div>
          <div class="stat-sub">校准 / 质控提醒</div>
        </AppCard>
      </el-col>
    </el-row>

    <AppCard title="业务台账概览" class="mt">
      <div class="mini-stats">
        <div class="mini" @click="go('/qc')">
          <span class="mini-num">{{ stats.qc }}</span>
          <span class="mini-label">质控记录</span>
        </div>
        <div class="mini" @click="go('/reagents')">
          <span class="mini-num">{{ stats.reagents }}</span>
          <span class="mini-label">试剂台账</span>
        </div>
        <div class="mini" @click="go('/training')">
          <span class="mini-num">{{ stats.training }}</span>
          <span class="mini-label">培训记录</span>
        </div>
        <div class="mini" @click="go('/verification')">
          <span class="mini-num">{{ stats.verification }}</span>
          <span class="mini-label">性能验证</span>
        </div>
        <div class="mini" @click="go('/iso15189')">
          <span class="mini-num">{{ stats.nc }}</span>
          <span class="mini-label">不符合项</span>
        </div>
      </div>
    </AppCard>

    <AppCard title="提醒事项" class="mt">
      <template #header-extra>
        <el-button
          v-if="notices.length"
          size="small"
          type="primary"
          :loading="sending"
          @click="onSendEmail"
        >发送提醒邮件</el-button>
        <el-button v-if="notices.length" size="small" @click="onReadAll">全部已读</el-button>
      </template>
      <el-empty v-if="!notices.length" description="暂无提醒" />
      <el-table v-else :data="notices" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="message" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="due_date" label="到期日" width="130" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button v-if="!row.is_read" link type="primary" @click="onRead(row)">标记已读</el-button>
            <el-tag v-else type="success" size="small">已读</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import AppCard from '../components/AppCard.vue'
import { listTestItems } from '../api/testItems'
import { listInstruments } from '../api/instruments'
import { listDocuments } from '../api/documents'
import { listNotifications, markRead, markAllRead, sendNotificationEmails } from '../api/notifications'
import { listQC } from '../api/qc'
import { listReagents } from '../api/reagents'
import { listTraining } from '../api/training'
import { listVerification } from '../api/verification'
import { listNC } from '../api/nonconformity'

const router = useRouter()
const stats = ref({
  testItems: '-', instruments: '-', documents: '-', notifications: '-',
  qc: '-', reagents: '-', training: '-', verification: '-', nc: '-',
})
const notices = ref([])
const sending = ref(false)

function levelType(level) {
  if (level === 'danger') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

function go(path) {
  router.push(path)
}

async function loadStats() {
  try {
    const [ti, ins, docs, notis, qc, rea, tr, ver, nc] = await Promise.all([
      listTestItems({ page: 1, page_size: 1 }),
      listInstruments({ page: 1, page_size: 1 }),
      listDocuments({ page: 1, page_size: 1 }),
      listNotifications({ page: 1, page_size: 1, unread_only: true }),
      listQC({ page: 1, page_size: 1 }),
      listReagents({ page: 1, page_size: 1 }),
      listTraining({ page: 1, page_size: 1 }),
      listVerification({ page: 1, page_size: 1 }),
      listNC({ page: 1, page_size: 1 }),
    ])
    stats.value = {
      testItems: ti.total,
      instruments: ins.total,
      documents: docs.total,
      notifications: notis.total,
      qc: qc.total,
      reagents: rea.total,
      training: tr.total,
      verification: ver.total,
      nc: nc.total,
    }
  } catch (e) {
    // 忽略
  }
}

async function loadNotices() {
  try {
    const res = await listNotifications({ page: 1, page_size: 50 })
    notices.value = res.items || []
  } catch (e) {
    notices.value = []
  }
}

async function onRead(row) {
  await markRead(row.id)
  row.is_read = true
  loadStats()
}
async function onReadAll() {
  await markAllRead()
  ElMessage.success('已全部标记已读')
  loadNotices()
  loadStats()
}

async function onSendEmail() {
  sending.value = true
  try {
    const res = await sendNotificationEmails()
    if (res.sent > 0) {
      ElMessage.success(`已发送邮件给 ${res.sent} 位接收人`)
    } else if (res.logged > 0) {
      ElMessage.warning('SMTP 未配置，已记录到服务端日志（降级模式）。请在环境变量配置 SMTP_HOST/USER/PASS 后重试。')
    } else if (res.detail) {
      ElMessage.info(res.detail)
    } else {
      ElMessage.info('当前没有未读提醒')
    }
  } catch (e) {
    ElMessage.error('发送失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  loadStats()
  loadNotices()
})
</script>

<style scoped>
.stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.stat .num {
  font-size: 34px;
  font-weight: 700;
  color: #1a365d;
}
.stat .num.warn {
  color: #e6a23c;
}
.stat .unit {
  color: #888;
}
.stat-sub {
  color: #999;
  font-size: 13px;
  margin-top: 4px;
}
.mt {
  margin-top: 16px;
}
.mini-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.mini {
  flex: 1;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 8px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.mini:hover {
  border-color: #1a365d;
  background: #f7fafc;
}
.mini-num {
  font-size: 26px;
  font-weight: 700;
  color: #1a365d;
}
.mini-label {
  color: #888;
  font-size: 13px;
  margin-top: 4px;
}
</style>
