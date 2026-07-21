<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">项目与仪器关联</h2>
      <p class="sub">
        将检验项目与试剂（含校准品/质控品）关联，耗材与仪器关联，便于后续试剂订购等开发。
        可先用「自动匹配」按名称批量生成，再在下方逐条审核、增删。
      </p>
    </div>

    <div class="toolbar">
      <el-button type="primary" :icon="MagicStick" :loading="matching" @click="onAutoMatch">自动匹配</el-button>
      <el-button :icon="Refresh" @click="refreshCurrent">刷新</el-button>
      <el-tag type="info" style="margin-left:8px">项目-试剂关联：{{ projTotal }} 条</el-tag>
      <el-tag type="info">仪器-耗材关联：{{ instTotal }} 条</el-tag>
    </div>

    <el-tabs v-model="activeTab" class="tabs">
      <!-- 项目 ↔ 试剂 -->
      <el-tab-pane label="项目 ↔ 试剂" name="project">
        <div class="toolbar">
          <el-input v-model="projQ" placeholder="搜索项目名/试剂名" clearable style="width:260px" @keyup.enter="loadProj" @clear="loadProj">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="projLibFilter" placeholder="全部责任库" clearable style="width:140px" @change="loadProj">
            <el-option label="生化凝血" value="生化凝血" />
            <el-option label="免疫" value="免疫" />
          </el-select>
          <el-select v-model="projAutoFilter" placeholder="全部来源" clearable style="width:140px" @change="loadProj">
            <el-option label="仅自动匹配" :value="true" />
            <el-option label="仅人工录入" :value="false" />
          </el-select>
          <el-button type="success" :icon="Plus" @click="openProjAdd" v-if="canWrite">新增关联</el-button>
        </div>
        <el-table v-loading="projLoading" :data="projFiltered" border stripe height="calc(100vh - 340px)" empty-text="暂无关联">
          <el-table-column type="index" width="50" label="#" />
          <el-table-column prop="test_item_name" label="检验项目" min-width="200" show-overflow-tooltip />
          <el-table-column prop="reagent_name" label="试剂/校准品/质控品" min-width="220" show-overflow-tooltip />
          <el-table-column prop="reagent_type" label="试剂类型" width="100" />
          <el-table-column prop="role" label="关联角色" width="110" />
          <el-table-column prop="reagent_library" label="责任库" width="100" />
          <el-table-column label="来源" width="100">
            <template #default="{ row }">
              <el-tag :type="row.auto_matched ? 'warning' : 'success'" size="small">{{ row.auto_matched ? '自动' : '人工' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" v-if="canWrite">
            <template #default="{ row }">
              <el-button size="small" link type="danger" @click="onDeleteProj(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination class="pager" v-model:current-page="projPage" v-model:page-size="projPageSize"
          :total="projTotal" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
          @current-change="loadProj" @size-change="projPage=1; loadProj()" />
      </el-tab-pane>

      <!-- 仪器 ↔ 耗材 -->
      <el-tab-pane label="仪器 ↔ 耗材" name="instrument">
        <div class="toolbar">
          <el-input v-model="instQ" placeholder="搜索仪器名/耗材名" clearable style="width:260px" @keyup.enter="loadInst" @clear="loadInst">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="success" :icon="Plus" @click="openInstAdd" v-if="canWrite">新增关联</el-button>
        </div>
        <el-table v-loading="instLoading" :data="instItems" border stripe height="calc(100vh - 340px)" empty-text="暂无关联">
          <el-table-column type="index" width="50" label="#" />
          <el-table-column prop="instrument_name" label="仪器" min-width="200" show-overflow-tooltip />
          <el-table-column prop="reagent_name" label="耗材" min-width="220" show-overflow-tooltip />
          <el-table-column prop="reagent_type" label="类型" width="100" />
          <el-table-column prop="role" label="关联角色" width="110" />
          <el-table-column label="来源" width="100">
            <template #default="{ row }">
              <el-tag :type="row.auto_matched ? 'warning' : 'success'" size="small">{{ row.auto_matched ? '自动' : '人工' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" v-if="canWrite">
            <template #default="{ row }">
              <el-button size="small" link type="danger" @click="onDeleteInst(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination class="pager" v-model:current-page="instPage" v-model:page-size="instPageSize"
          :total="instTotal" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
          @current-change="loadInst" @size-change="instPage=1; loadInst()" />
      </el-tab-pane>
    </el-tabs>

    <!-- 新增 项目-试剂 关联 -->
    <el-dialog v-model="projAddVisible" title="新增 项目-试剂 关联" width="560px">
      <el-form label-width="90px" size="small">
        <el-form-item label="检验项目" required>
          <el-select v-model="projForm.test_item_id" filterable placeholder="选择项目" style="width:100%">
            <el-option v-for="o in testItemOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="试剂" required>
          <el-select v-model="projForm.reagent_item_id" filterable placeholder="选择试剂（试剂/校准品/质控品）" style="width:100%">
            <el-option v-for="o in reagentOptionsNonCons" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联角色">
          <el-select v-model="projForm.role" style="width:100%">
            <el-option label="试剂" value="试剂" />
            <el-option label="校准品" value="校准品" />
            <el-option label="质控品" value="质控品" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projAddVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onProjSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增 仪器-耗材 关联 -->
    <el-dialog v-model="instAddVisible" title="新增 仪器-耗材 关联" width="560px">
      <el-form label-width="90px" size="small">
        <el-form-item label="仪器" required>
          <el-select v-model="instForm.instrument_id" filterable placeholder="选择仪器" style="width:100%">
            <el-option v-for="o in instrumentOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="耗材" required>
          <el-select v-model="instForm.reagent_item_id" filterable placeholder="选择耗材" style="width:100%">
            <el-option v-for="o in reagentOptionsCons" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="instAddVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onInstSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, MagicStick } from '@element-plus/icons-vue'
import {
  listTestItemReagents, createTestItemReagent, deleteTestItemReagent,
  listInstrumentReagents, createInstrumentReagent, deleteInstrumentReagent,
  autoMatchAssociations,
} from '../../api/reagent'
import { listTestItems } from '../../api/testItems'
import { listReagentItems } from '../../api/reagent'
import { listInstruments } from '../../api/instruments'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))

const activeTab = ref('project')

// 下拉数据
const testItemOptions = ref([])
const instrumentOptions = ref([])
const reagentOptionsAll = ref([])
const reagentOptionsNonCons = computed(() => reagentOptionsAll.value.filter(o => o.type !== '耗材'))
const reagentOptionsCons = computed(() => reagentOptionsAll.value.filter(o => o.type === '耗材'))

// 项目-试剂
const projItems = ref([]), projTotal = ref(0), projPage = ref(1), projPageSize = ref(50)
const projLoading = ref(false), projQ = ref(''), projLibFilter = ref(''), projAutoFilter = ref(null)
const projFiltered = computed(() => {
  let arr = projItems.value
  if (projLibFilter.value) arr = arr.filter(r => r.reagent_library === projLibFilter.value)
  return arr
})

// 仪器-耗材
const instItems = ref([]), instTotal = ref(0), instPage = ref(1), instPageSize = ref(50)
const instLoading = ref(false), instQ = ref('')

const matching = ref(false)
const submitting = ref(false)
const projAddVisible = ref(false), instAddVisible = ref(false)
const projForm = reactive({ test_item_id: null, reagent_item_id: null, role: '试剂' })
const instForm = reactive({ instrument_id: null, reagent_item_id: null, role: '耗材' })

async function loadOptions() {
  try {
    const [ti, ri, ins] = await Promise.all([
      listTestItems({ page: 1, page_size: 300 }),
      listReagentItems({ page: 1, page_size: 500 }),
      listInstruments({ page: 1, page_size: 100 }),
    ])
    testItemOptions.value = (ti.items || []).map(t => ({ value: t.id, label: t.name }))
    reagentOptionsAll.value = (ri.items || []).map(r => ({ value: r.id, label: `${r.name}（${r.type}）`, type: r.type }))
    instrumentOptions.value = (ins.items || []).map(i => ({ value: i.id, label: i.name }))
  } catch (e) {
    ElMessage.error('加载下拉数据失败：' + (e?.response?.data?.detail || e.message))
  }
}

async function loadProj() {
  projLoading.value = true
  try {
    const params = { page: projPage.value, page_size: projPageSize.value }
    if (projQ.value.trim()) params.q = projQ.value.trim()
    if (projAutoFilter.value !== null) params.auto_only = projAutoFilter.value
    const r = await listTestItemReagents(params)
    projItems.value = r.items; projTotal.value = r.total
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally { projLoading.value = false }
}

async function loadInst() {
  instLoading.value = true
  try {
    const params = { page: instPage.value, page_size: instPageSize.value }
    if (instQ.value.trim()) params.q = instQ.value.trim()
    const r = await listInstrumentReagents(params)
    instItems.value = r.items; instTotal.value = r.total
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally { instLoading.value = false }
}

function refreshCurrent() {
  if (activeTab.value === 'project') loadProj(); else loadInst()
}

async function onAutoMatch() {
  try {
    await ElMessageBox.confirm('将按名称自动匹配生成关联（已存在的关联不会重复生成）。是否继续？', '自动匹配', { type: 'info' })
  } catch { return }
  matching.value = true
  try {
    const r = await autoMatchAssociations(false)
    const msg = `新增 项目-试剂 ${r.test_item_reagents_added} 条、仪器-耗材 ${r.instrument_reagents_added} 条；`
      + `未能自动匹配：项目侧 ${r.test_item_unmatched.length} 个、仪器侧 ${r.instrument_unmatched.length} 个（可人工补录）。`
    ElMessage.success(msg)
    loadProj(); loadInst()
  } catch (e) {
    ElMessage.error('自动匹配失败：' + (e?.response?.data?.detail || e.message))
  } finally { matching.value = false }
}

function openProjAdd() {
  Object.assign(projForm, { test_item_id: null, reagent_item_id: null, role: '试剂' })
  projAddVisible.value = true
}
function openInstAdd() {
  Object.assign(instForm, { instrument_id: null, reagent_item_id: null, role: '耗材' })
  instAddVisible.value = true
}
async function onProjSubmit() {
  if (!projForm.test_item_id || !projForm.reagent_item_id) { ElMessage.warning('请选择项目与试剂'); return }
  submitting.value = true
  try {
    await createTestItemReagent({ ...projForm, auto_matched: false })
    ElMessage.success('已新增'); projAddVisible.value = false; loadProj()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally { submitting.value = false }
}
async function onInstSubmit() {
  if (!instForm.instrument_id || !instForm.reagent_item_id) { ElMessage.warning('请选择仪器与耗材'); return }
  submitting.value = true
  try {
    await createInstrumentReagent({ ...instForm, auto_matched: false })
    ElMessage.success('已新增'); instAddVisible.value = false; loadInst()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally { submitting.value = false }
}
async function onDeleteProj(row) {
  await ElMessageBox.confirm(`确认删除「${row.test_item_name} ↔ ${row.reagent_name}」？`, '提示', { type: 'warning' })
  await deleteTestItemReagent(row.id); ElMessage.success('已删除'); loadProj()
}
async function onDeleteInst(row) {
  await ElMessageBox.confirm(`确认删除「${row.instrument_name} ↔ ${row.reagent_name}」？`, '提示', { type: 'warning' })
  await deleteInstrumentReagent(row.id); ElMessage.success('已删除'); loadInst()
}

onMounted(() => { loadOptions(); loadProj(); loadInst() })
</script>

<style scoped>
.page { padding: 16px 20px 0; display: flex; flex-direction: column; height: 100%; }
.page-header { margin-bottom: 8px; }
.title { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0; color: #64748b; font-size: 13px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin: 8px 0 12px; flex-wrap: wrap; }
.tabs { flex: 1; display: flex; flex-direction: column; }
.pager { margin: 10px 0 16px; display: flex; justify-content: flex-end; }
</style>
