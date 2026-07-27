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

    <AppCard title="今日我的岗位" class="mt">
      <template #header-extra>
        <el-radio-group v-model="rangeMode" size="small" @change="onRangeChange">
          <el-radio-button label="week">本周</el-radio-button>
          <el-radio-button label="fortnight">近两周</el-radio-button>
          <el-radio-button label="month">本月</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="loadMyShifts">刷新</el-button>
        <el-button size="small" type="primary" plain @click="go('/scheduling?tab=month')">换班申请</el-button>
        <el-button size="small" type="warning" plain @click="go('/scheduling?tab=rest')">休息申请</el-button>
      </template>

      <div v-if="myShifts.length" class="my-shifts">
        <el-tag
          v-for="m in myShifts"
          :key="m.post_id"
          :type="m.group === 'night' ? 'danger' : (m.group === 'special' ? 'warning' : 'primary')"
          effect="light"
          class="shift-chip"
        >
          {{ m.post_name }}
          <template v-if="m.is_early"><span class="tag-sub">早班</span></template>
          <template v-if="m.is_continuous"><span class="tag-sub">连班</span></template>
          <span v-if="m.status && m.status !== '在岗'" class="tag-sub">{{ m.status }}</span>
        </el-tag>
        <el-button class="shift-more" size="small" text type="primary" @click="go('/scheduling')">查看完整排班表</el-button>
      </div>
      <el-divider v-if="myShifts.length && mySchedule.length" />

      <el-empty v-if="!mySchedule.length" description="该范围内暂无排班记录" :image-size="60" />
      <el-table v-else :data="mySchedule" size="small" style="width: 100%">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="星期" width="80">
          <template #default="{ row }">{{ weekdayLabel(row.weekday) }}</template>
        </el-table-column>
        <el-table-column label="岗位 / 状态" min-width="150">
          <template #default="{ row }">
            <span v-if="row.post_name">{{ row.post_name }}</span>
            <span v-else class="muted">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="班次类型" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_early" size="small" type="warning">早班</el-tag>
            <el-tag v-else-if="row.is_continuous" size="small" type="danger">连班</el-tag>
            <span v-else-if="row.status && row.status !== '在岗'" class="muted">{{ row.status }}</span>
            <span v-else class="muted">白班</span>
          </template>
        </el-table-column>
        <el-table-column label="换班" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_locked" size="small" type="info">已换班</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>

      <el-divider v-if="mySchedule.length && restRoster.length" />
      <div v-if="restRoster.length" class="rest-roster">
        <div class="rest-roster-title">本范围休息人员（{{ rangeLabel }}）</div>
        <div class="rest-chips">
          <el-tag
            v-for="r in restRoster"
            :key="r.date + '|' + r.person"
            type="info"
            effect="plain"
            size="small"
            class="rest-chip"
          >{{ r.date }} · {{ r.person }}</el-tag>
        </div>
      </div>
      <el-empty v-else-if="mySchedule.length" description="本范围无人申请休息" :image-size="50" />
    </AppCard>

    <AppCard title="提醒事项" class="mt">
      <template #header-extra>
        <el-radio-group v-model="showAll" size="small" @change="loadNotices">
          <el-radio-button :label="false">仅未读</el-radio-button>
          <el-radio-button :label="true">全部</el-radio-button>
        </el-radio-group>
        <el-button v-if="!showAll && notices.length" size="small" type="primary" plain @click="onReadAll">全部已读</el-button>
        <el-button v-if="showAll && hasRead" size="small" @click="onUnreadAll">全部标为未读</el-button>
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
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button v-if="!row.is_read" link type="primary" @click="onRead(row)">标记已读</el-button>
            <template v-else>
              <el-tag type="success" size="small">已读</el-tag>
              <el-button link type="warning" size="small" @click="onUnread(row)">标记未读</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </AppCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import AppCard from '../components/AppCard.vue'
import { getDashboardStats } from '../api/dashboard'
import { listTestItems } from '../api/testItems'
import { listInstruments } from '../api/instruments'
import { listDocuments } from '../api/documents'
import { listNotifications, markRead, markAllRead, markUnread, markAllUnread } from '../api/notifications'
import { listQC } from '../api/qc'
import { listReagents } from '../api/reagents'
import { listTraining } from '../api/training'
import { listVerification } from '../api/verification'
import { listNC } from '../api/nonconformity'
import { getMyToday, getMySchedule, getRestRoster } from '../api/scheduling'

const router = useRouter()
const stats = ref({
  testItems: '-', instruments: '-', documents: '-', notifications: '-',
  qc: '-', reagents: '-', training: '-', verification: '-', nc: '-',
})
const notices = ref([])
const myShifts = ref([])
const mySchedule = ref([])
const restRoster = ref([])   // 本范围休息人员花名册
const rangeMode = ref('week')  // week / fortnight / month
const showAll = ref(false)  // false=仅未读（默认隐藏已读），true=显示全部
const hasRead = computed(() => notices.value.some(n => n.is_read))
const rangeLabel = computed(() => ({ week: '本周', fortnight: '近两周', month: '本月' }[rangeMode.value] || ''))

function levelType(level) {
  if (level === 'danger') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
function weekdayLabel(w) {
  return WEEKDAYS[w] ?? ''
}

function go(path) {
  router.push(path)
}

async function loadStats() {
  // 优先使用聚合统计接口（单次请求，鉴权面最小）
  try {
    const data = await getDashboardStats()
    stats.value = {
      testItems: data.test_items ?? '-',
      instruments: data.instruments ?? '-',
      documents: data.documents ?? '-',
      notifications: data.unread_notifications ?? '-',
      qc: data.qc_records ?? '-',
      reagents: data.reagents ?? '-',
      training: data.training_records ?? '-',
      verification: data.verification_records ?? '-',
      nc: data.nonconformities ?? '-',
    }
    return
  } catch (_) {
    // 聚合接口失败，回退到逐个请求
  }

  // 回退：用 allSettled 确保单个接口失败不影响其他卡片
  const results = await Promise.allSettled([
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
  const keys = ['testItems', 'instruments', 'documents', 'notifications', 'qc', 'reagents', 'training', 'verification', 'nc']
  const updated = {}
  results.forEach((r, i) => {
    updated[keys[i]] = r.status === 'fulfilled' ? r.value.total : '-'
  })
  stats.value = updated
}

async function loadNotices() {
  try {
    const res = await listNotifications({ page: 1, page_size: 50, unread_only: !showAll.value })
    notices.value = res.items || []
  } catch (e) {
    notices.value = []
  }
}

async function loadMyShifts() {
  try {
    myShifts.value = await getMyToday()
  } catch (e) {
    myShifts.value = []
  }
}

async function loadMySchedule() {
  try {
    mySchedule.value = await getMySchedule({ range: rangeMode.value })
  } catch (e) {
    mySchedule.value = []
  }
}

async function loadRestRoster() {
  try {
    restRoster.value = await getRestRoster({ range: rangeMode.value })
  } catch (e) {
    restRoster.value = []
  }
}

// 切换范围时同步刷新「我的排班」与「休息花名册」
function onRangeChange() {
  loadMySchedule()
  loadRestRoster()
}

async function onRead(row) {
  await markRead(row.id)
  // 默认「仅未读」视图下，已读后该项应隐藏，重新拉取列表
  await loadNotices()
  loadStats()
}
async function onUnread(row) {
  await markUnread(row.id)
  await loadNotices()
  loadStats()
}
async function onReadAll() {
  await markAllRead()
  ElMessage.success('已全部标记已读')
  loadNotices()
  loadStats()
}
async function onUnreadAll() {
  await markAllUnread()
  ElMessage.success('已全部恢复为未读')
  loadNotices()
  loadStats()
}

onMounted(() => {
  loadStats()
  loadNotices()
  loadMyShifts()
  loadMySchedule()
  loadRestRoster()
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
.my-shifts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.shift-chip {
  font-size: 14px;
  padding: 6px 10px;
}
.shift-more {
  margin-left: 4px;
}
.tag-sub {
  margin-left: 4px;
  opacity: 0.8;
  font-size: 12px;
}
.muted {
  color: #999;
  font-size: 13px;
}
.rest-roster {
  margin-top: 4px;
}
.rest-roster-title {
  font-size: 13px;
  color: #666;
  font-weight: 600;
  margin-bottom: 8px;
}
.rest-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.rest-chip {
  font-weight: 500;
}
</style>
