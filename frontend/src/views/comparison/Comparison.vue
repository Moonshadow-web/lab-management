<template>
  <div class="cmp-page">
    <div class="toolbar">
      <el-button :icon="EditPen" @click="openGroupEdit" :disabled="!selectedGroup" v-if="canWrite">编辑分组</el-button>
      <el-button type="danger" :icon="Delete" @click="onDeleteGroup" :disabled="!selectedGroup" v-if="canWrite">删除分组</el-button>
      <el-button type="primary" :icon="Plus" @click="openGroupCreate" v-if="canWrite">新建分组</el-button>
      <el-select v-model="selectedGroupId" filterable placeholder="选择比对分组" style="width:300px"
        @change="onGroupChange">
        <el-option v-for="g in groups" :key="g.id" :label="`${g.name}（${g.form_code}）`" :value="g.id" />
      </el-select>
      <el-tag type="info" v-if="selectedGroup">类型：{{ selectedGroup.category }}｜水平：{{ selectedGroup.levels }}｜项目：{{ selectedGroup.items.length }}</el-tag>
      <div style="flex:1" />
      <el-button type="success" :icon="Plus" @click="openPlanCreate" :disabled="!selectedGroup" v-if="canWrite">新建计划</el-button>
    </div>

    <el-alert v-if="!selectedGroup" type="info" :closable="false" show-icon
      title="请先选择或新建一个比对分组。系统已预设：生化分析仪/ DXI800 / 凝血 / 早孕系列 / 血气 / 定性 等分组（对应 BG-SM-CZ-021/024~027/071）。" />

    <el-table v-else :data="plans" border size="small" style="margin-top:12px">
      <el-table-column label="年份" width="80" prop="year" />
      <el-table-column label="半年" width="80">
        <template #default="{ row }">
          {{ row.half === 1 ? '上半年' : '下半年' }}
        </template>
      </el-table-column>
      <el-table-column label="靶机" width="150" prop="reference_instrument_name" show-overflow-tooltip />
      <el-table-column label="项目" min-width="200">
        <template #default="{ row }">
          <el-tooltip v-if="row.compared_items && row.compared_items.length" placement="top" :show-after="200">
            <template #content>
              <div style="max-width:400px;line-height:1.6">
                已做：{{ row.compared_items.join('、') }}<br />
                共 {{ row.compared_count }}/{{ row.group_total }} 项
              </div>
            </template>
            <span class="items-line">
              <span v-if="row.compared_count <= 6">{{ row.compared_items.join('、') }}</span>
              <span v-else>{{ row.compared_items.slice(0, 6).join('、') }}…</span>
              <el-tag size="small" :type="row.compared_count === row.group_total ? 'success' : 'info'" effect="plain" style="margin-left:4px">
                {{ row.compared_count }}/{{ row.group_total }}
              </el-tag>
            </span>
          </el-tooltip>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="compared_at" label="比对日期" width="110" />
      <el-table-column prop="operator" label="操作者" width="90" />
      <el-table-column prop="reviewer" label="审核者" width="90" />
      <el-table-column prop="conclusion" label="结论" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.conclusion === '可接受'" type="success" size="small">可接受</el-tag>
          <el-tag v-else-if="row.conclusion === '不可接受'" type="danger" size="small">不可接受</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="报告" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.report_filename" type="primary" size="small" effect="plain">已生成</el-tag>
          <span v-else class="muted">未生成</span>
        </template>
      </el-table-column>
      <el-table-column label="原始结果" width="110" align="center">
        <template #default="{ row }">
          <el-badge v-if="row.attachment_count" :value="row.attachment_count" :max="99" type="primary">
            <el-button size="small" @click="openAttachments(row)">附件</el-button>
          </el-badge>
          <el-button v-else size="small" plain @click="openAttachments(row)" v-if="canWrite">+上传</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEntry(row)" v-if="canWrite">录入</el-button>
          <el-button size="small" type="warning" @click="openReport(row)">报告管理</el-button>
          <el-button size="small" @click="openPlanEdit(row)" v-if="canWrite">编辑</el-button>
          <el-button size="small" type="danger" @click="onDeletePlan(row)" v-if="canWrite">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <GroupDialog v-model:visible="groupVisible" :group="editingGroup" :instruments="instruments"
      @close="groupVisible = false" @saved="onGroupSaved" />
    <PlanDialog v-model:visible="planVisible" :plan="editingPlan" :groups="groups"
      :default-group-id="selectedGroupId" @close="planVisible = false" @saved="onPlanSaved" />
    <ResultEntry v-if="entryVisible" :visible="entryVisible" :plan="activePlan" :group="selectedGroup"
      @close="entryVisible = false" @saved="reloadPlans" />
    <ReportPanel v-if="reportVisible" :visible="reportVisible" :plan="activePlan" :group-name="selectedGroup?.name"
      @close="reportVisible = false" @saved="reloadPlans" />
    <AttachmentsDialog v-if="attachVisible" :visible="attachVisible" :plan="activePlan"
      @close="attachVisible = false" @changed="reloadPlans" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete } from '@element-plus/icons-vue'
import {
  listGroups, deleteGroup, listPlans, deletePlan, updatePlan, instrumentOptions,
} from '../../api/comparison'
import { useAuthStore } from '../../store/auth'
import { usePermissionStore } from '../../store/permission'
import GroupDialog from './GroupDialog.vue'
import PlanDialog from './PlanDialog.vue'
import ResultEntry from './ResultEntry.vue'
import ReportPanel from './ReportPanel.vue'
import AttachmentsDialog from './AttachmentsDialog.vue'

const auth = useAuthStore()
const perm = usePermissionStore()
const canWrite = computed(() => perm.canWrite(auth.userRoles, 'comparison'))
const canEdit = computed(() => perm.canWrite(auth.userRoles, 'comparison-edit'))

const groups = ref([])
const instruments = ref([])
const selectedGroupId = ref(null)
const plans = ref([])

const groupVisible = ref(false)
const editingGroup = ref(null)
const planVisible = ref(false)
const editingPlan = ref(null)
const entryVisible = ref(false)
const reportVisible = ref(false)
const attachVisible = ref(false)
const activePlan = ref(null)

const selectedGroup = computed(() => groups.value.find((g) => g.id === selectedGroupId.value))

async function loadGroups() {
  groups.value = await listGroups()
  if (!selectedGroupId.value && groups.value.length) {
    selectedGroupId.value = groups.value[0].id
    await reloadPlans()
  }
}
async function loadInstruments() {
  try {
    const r = await instrumentOptions()
    // name 已是可识别型号；带上 model / status 供分组选择显示与筛选
    instruments.value = (r || []).map((i) => ({
      id: i.id, name: i.name, model: i.model, status: i.status,
    }))
  } catch (e) { /* ignore */ }
}
async function reloadPlans() {
  if (!selectedGroupId.value) return
  const r = await listPlans({ group_id: selectedGroupId.value })
  plans.value = r.items || []
}

function onGroupChange() { reloadPlans() }

function openGroupCreate() { editingGroup.value = null; groupVisible.value = true }
function openGroupEdit() { editingGroup.value = selectedGroup.value; groupVisible.value = true }
function onGroupSaved() {
  loadGroups()
  ElMessage.success('分组已更新')
}
async function onDeleteGroup() {
  try {
    await ElMessageBox.confirm(`确认删除分组「${selectedGroup.value.name}」及其下所有计划？`, '警告', { type: 'warning' })
  } catch { return }
  try {
    await deleteGroup(selectedGroup.value.id)
    ElMessage.success('已删除')
    selectedGroupId.value = null
    await loadGroups()
  } catch (e) { ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message)) }
}

function openPlanCreate() { editingPlan.value = null; planVisible.value = true }
function openPlanEdit(row) { editingPlan.value = row; planVisible.value = true }
function onPlanSaved() { reloadPlans() }
async function onDeletePlan(row) {
  try {
    await ElMessageBox.confirm(`确认删除该比对计划（${row.year}年 半年${row.half}）？`, '警告', { type: 'warning' })
  } catch { return }
  try {
    await deletePlan(row.id)
    ElMessage.success('已删除')
    reloadPlans()
  } catch (e) { ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message)) }
}

function openEntry(row) { activePlan.value = row; entryVisible.value = true }
function openReport(row) { activePlan.value = row; reportVisible.value = true }
function openAttachments(row) { activePlan.value = row; attachVisible.value = true }
async function onInlineEdit(row, patch) {
  try {
    await updatePlan(row.id, patch)
    ElMessage.success('已更新')
  } catch (e) {
    ElMessage.error('更新失败：' + (e.response?.data?.detail || e.message))
    reloadPlans()
  }
}

onMounted(() => { loadGroups(); loadInstruments() })
</script>

<style scoped>
.cmp-page { padding: 4px; }
.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.yes { color: #27ae60; font-weight: 700; }
.no { color: #c0392b; font-weight: 700; }
.muted { color: #999; }
.items-line { display: inline-block; max-width: 100%; vertical-align: middle; }
@media (max-width: 768px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar .el-select { width: 100% !important; }
}
</style>
