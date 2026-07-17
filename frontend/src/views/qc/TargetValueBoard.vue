<template>
  <div class="target-board">
    <!-- 工具栏 -->
    <div class="tb">
      <el-select v-model="filterMaterial" placeholder="质控品" clearable filterable allow-create
        style="width:200px" @change="loadBatches">
        <el-option v-for="m in presets" :key="m" :label="m" :value="m" />
      </el-select>
      <el-select v-model="filterMode" placeholder="模式" clearable style="width:130px" @change="loadBatches">
        <el-option label="录入" value="entry" />
        <el-option label="存档" value="archive" />
      </el-select>
      <el-select v-model="filterMethod" placeholder="方法" clearable style="width:130px" @change="loadBatches">
        <el-option label="常规法" value="conventional" />
        <el-option label="即刻法" value="immediate" />
      </el-select>
      <el-input v-model="kw" placeholder="搜索批号/仪器" clearable style="width:180px" @keyup.enter="loadBatches" @clear="loadBatches" />
      <el-button type="primary" @click="loadBatches">查询</el-button>
      <el-button v-if="auth.canWrite('qc')" type="success" @click="openNew">+ 新建批号</el-button>
      <el-button v-if="auth.canWrite('qc')" @click="openMatManage">质控品管理</el-button>
      <span class="tb-hint">一盒质控品一条批号（同质控品不同批号共享项目清单）；生化多项仅存档，其余录入结果按所选方法累计靶值。</span>
    </div>

    <!-- 列表 -->
    <el-table :data="rows" v-loading="loading" border stripe>
      <el-table-column prop="qc_material" label="质控品" min-width="150" />
      <el-table-column prop="lot_no" label="批号" width="120" />
      <el-table-column label="水平" width="70" align="center">
        <template #default="{ row }">
          <span v-if="row.level && row.level > 0">{{ row.level }}</span>
          <span v-else class="lv-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="instrument" label="仪器" width="130" />
      <el-table-column label="方法" width="90">
        <template #default="{ row }">
          <span v-if="row.mode === 'archive'">—</span>
          <el-tag v-else size="small" :type="row.method === 'immediate' ? 'warning' : 'info'">
            {{ row.method === 'immediate' ? '即刻法' : '常规法' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="模式" width="80">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.mode === 'archive' ? '存档' : '录入' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="录入次数" width="90" align="center">
        <template #default="{ row }">{{ row._entries ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row._status)">{{ row._status || '—' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">查看/录入</el-button>
          <el-button v-if="row.archive_filename" link type="success" @click="previewArchive(row)">预览存档</el-button>
          <el-button v-if="auth.canWrite('qc')" link type="danger" @click="removeBatch(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev,pager,next,total"
        @current-change="loadBatches" />
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑批号' : '新建批号累积靶值'" width="560px" append-to-body>
      <el-form label-width="92px">
        <el-form-item label="质控品" required>
          <div class="mat-pick">
            <el-select v-model="editForm.qc_material_id" filterable placeholder="选择质控品" style="width:100%"
              @change="onMaterialPick">
              <el-option v-for="m in materials" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
            <el-button link type="primary" @click="openMatManage()">+ 新建质控品</el-button>
          </div>
          <div class="form-tip" v-if="currentMatItems.length">
            该项目含：{{ currentMatItems.join('、') }}
          </div>
        </el-form-item>
        <el-form-item label="批号" required>
          <el-input v-model="editForm.lot_no" placeholder="如 20260101" />
        </el-form-item>
        <el-form-item label="水平">
          <el-select v-model="editForm.level" style="width:100%">
            <el-option label="未指定" :value="0" />
            <el-option label="水平 1" :value="1" />
            <el-option label="水平 2" :value="2" />
            <el-option label="水平 3" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="仪器">
          <el-input v-model="editForm.instrument" placeholder="如 DXI800 / AU5800" />
        </el-form-item>
        <el-form-item label="方法">
          <el-select v-model="editForm.method" :disabled="editForm.qc_material === '生化多项质控品'" style="width:100%">
            <el-option label="常规法（≥10暂定，≥20确立）" value="conventional" />
            <el-option label="即刻法（≥3次起判，累计20次）" value="immediate" />
          </el-select>
          <div class="form-tip" v-if="editForm.qc_material === '生化多项质控品'">
            生化多项质控品仅做存档（上传PDF），不录入结果，方法无意义。
          </div>
        </el-form-item>
        <el-form-item label="备注/靶值说明">
          <el-input v-model="editForm.note" type="textarea" :rows="2" placeholder="如靶值来源说明、备注" />
        </el-form-item>
        <el-form-item label="存档PDF">
          <input type="file" accept="application/pdf" @change="onArchivePick" />
          <div v-if="archiveFile" class="file-tip">已选：{{ archiveFile.name }}</div>
          <div v-else-if="editForm.id && currentArchive" class="file-tip muted">当前：{{ currentArchive }}</div>
          <div class="form-tip">生化多项质控品建议上传靶值记录PDF存档（可预览）。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBatch">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情/录入对话框 -->
    <el-dialog v-model="detailVisible" :title="`批号累积靶值 - ${detailRow?.qc_material || ''} ${detailRow?.lot_no || ''}`"
      width="92%" top="3vh" append-to-body @close="onDetailClose">
      <div v-if="detailRow" v-loading="detailLoading">
        <div class="d-info">
          <span>水平：<b v-if="detailRow.level && detailRow.level > 0">{{ detailRow.level }}</b><span v-else>—</span></span>
          <span>仪器：{{ detailRow.instrument || '—' }}</span>
          <span>方法：{{ detailRow.mode === 'archive' ? '存档' : (detailRow.method === 'immediate' ? '即刻法' : '常规法') }}</span>
          <span>状态：<el-tag :type="statusType(stats.batch_status)" size="small">{{ stats.batch_status }}</el-tag></span>
          <span>录入 {{ stats.total_entries }} 次</span>
          <span v-if="stats.out_count">失控标记 {{ stats.out_count }}</span>
        </div>

        <!-- 存档模式：仅预览 + 备注 -->
        <template v-if="detailRow.mode === 'archive'">
          <el-alert type="info" :closable="false" show-icon title="生化多项质控品：仅存档，不录入结果。" style="margin:8px 0" />
          <div class="d-note">
            <div class="d-note-label">靶值说明：</div>
            <el-input v-model="detailRow.note" type="textarea" :rows="2" @blur="saveNote" />
          </div>
          <div class="pdf-wrap" v-if="archiveUrl">
            <iframe :src="archiveUrl" style="width:100%;height:60vh;border:none" />
          </div>
          <el-empty v-else description="未上传存档 PDF" />
          <div v-if="auth.canWrite('qc')" style="margin-top:8px">
            <input type="file" accept="application/pdf" @change="onDetailArchivePick" />
            <el-button size="small" type="primary" :loading="archSaving" @click="uploadDetailArchive">上传/替换存档</el-button>
          </div>
        </template>

        <!-- 录入模式 -->
        <template v-else>
          <!-- 各项目累计统计卡 -->
          <div class="ana-cards">
            <div class="ana-card" v-for="a in stats.analytes" :key="a">
              <div class="ana-name">
                {{ a }}
                <el-tag v-if="stats.per_analyte[a].manual" size="small" type="success" style="margin-left:4px">手动</el-tag>
              </div>
              <div class="ana-row"><span>次数</span><b>{{ stats.per_analyte[a].n }}</b></div>
              <div class="ana-row"><span>均值</span><b>{{ stats.per_analyte[a].mean }}</b></div>
              <div class="ana-row"><span>SD</span><b>{{ stats.per_analyte[a].sd }}</b></div>
              <div class="ana-row"><span>CV%</span><b>{{ stats.per_analyte[a].cv }}</b></div>
              <div class="ana-row"><span>状态</span>
                <el-tag :type="statusType(stats.per_analyte[a].status)" size="small">{{ stats.per_analyte[a].status }}</el-tag>
              </div>
              <el-button v-if="stats.per_analyte[a].can_establish && !stats.per_analyte[a].established"
                size="small" type="success" plain @click="doEstablish">确立靶值</el-button>
            </div>
            <el-empty v-if="!stats.analytes.length" description="尚未录入结果" :image-size="60" />
          </div>

          <!-- 录入区 -->
          <div v-if="auth.canWrite('qc')" class="entry">
            <el-select v-model="resultForm.analyte" filterable allow-create placeholder="项目/分析物" style="width:200px">
              <el-option-group label="质控品项目">
                <el-option v-for="a in stats.material_items" :key="'m_' + a" :label="a" :value="a" />
              </el-option-group>
              <el-option-group label="已录入">
                <el-option v-for="a in stats.analytes" :key="'e_' + a" :label="a" :value="a" />
              </el-option-group>
            </el-select>
            <el-input v-model="resultForm.value" type="number" placeholder="测定值" style="width:140px" @keyup.enter="submitResult" />
            <el-date-picker v-model="resultForm.qc_date" type="date" value-format="YYYY-MM-DD" placeholder="日期" style="width:160px" />
            <el-button type="primary" :loading="adding" @click="submitResult">录入</el-button>
          </div>

          <el-alert v-if="lastNote" :type="lastNoteType" :closable="true" show-icon :title="lastNote" style="margin:8px 0" />

          <!-- 历史表 -->
          <el-table :data="resultRows" border size="small" style="margin-top:8px">
            <el-table-column prop="seq" label="#" width="50" align="center" />
            <el-table-column prop="analyte" label="项目" width="150" />
            <el-table-column prop="value" label="测定值" width="110" />
            <el-table-column prop="qc_date" label="日期" width="120" />
            <el-table-column label="SI上限" width="90">
              <template #default="{ row }">{{ row.si_upper ? row.si_upper : '—' }}</template>
            </el-table-column>
            <el-table-column label="SI下限" width="90">
              <template #default="{ row }">{{ row.si_lower ? row.si_lower : '—' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="170" v-if="auth.canWrite('qc')">
              <template #default="{ row }">
                <template v-if="row.is_out">
                  <el-button link type="success" size="small" @click="toggleRow(row)">人工确认</el-button>
                  <el-tag size="small" type="danger">失控</el-tag>
                </template>
                <template v-else-if="row.manual">
                  <el-button link type="warning" size="small" @click="toggleRow(row)">取消确认</el-button>
                  <el-tag size="small" type="success">人工确认</el-tag>
                </template>
                <template v-else>
                  <el-button link type="warning" size="small" @click="toggleRow(row)">标记失控</el-button>
                </template>
                <el-button link type="danger" size="small" @click="delRow(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-dialog>

    <!-- 质控品管理对话框 -->
    <el-dialog v-model="matManageVisible" title="质控品管理" width="680px" top="5vh" append-to-body>
      <div class="mat-toolbar" v-if="auth.canWrite('qc')">
        <el-button type="primary" size="small" @click="openMatNew">+ 新建质控品</el-button>
        <span class="form-tip">同一种质控品（不同批号）共享同一份项目清单；建批选质控品后，录入结果的分析物下拉即由它预填。</span>
      </div>
      <el-table :data="materials" border size="small" v-loading="matLoading" style="margin-top:8px">
        <el-table-column prop="name" label="质控品" min-width="140" />
        <el-table-column label="包含项目" min-width="240">
          <template #default="{ row }">
            <el-tag v-for="it in (row.items || [])" :key="it" size="small" style="margin:2px">{{ it }}</el-tag>
            <span v-if="!row.items || !row.items.length" class="lv-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" v-if="auth.canWrite('qc')">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openMatEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="delMat(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 新建/编辑质控品 -->
      <el-dialog v-model="matEditVisible" :title="matForm.id ? '编辑质控品' : '新建质控品'" width="460px" append-to-body>
        <el-form label-width="84px">
          <el-form-item label="名称" required>
            <el-input v-model="matForm.name" placeholder="如 伯乐免疫多项" />
          </el-form-item>
          <el-form-item label="包含项目">
            <el-input v-model="matItemsText" type="textarea" :rows="6" placeholder="每行一个项目，如：&#10;ALT&#10;AST&#10;肌酐" />
            <div class="form-tip">同一质控品的不同批号共享此项目清单；录入结果时作为分析物下拉候选（仍可手填其他项）。</div>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="matForm.note" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="matEditVisible = false">取消</el-button>
          <el-button type="primary" :loading="matSaving" @click="saveMat">保存</el-button>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../../store/auth'
import {
  listTargetBatches, createTargetBatch, updateTargetBatch, deleteTargetBatch,
  getMaterialPresets, addTargetResult, listTargetResults, deleteTargetResult,
  toggleTargetResult, establishTarget, uploadTargetArchive, downloadTargetArchive,
} from '../../api/qc_target'
import {
  listQcMaterials, createQcMaterial, updateQcMaterial, deleteQcMaterial,
} from '../../api/qc_material'

const auth = useAuthStore()
const ARCHIVE_MATERIAL = '生化多项质控品'

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const presets = ref([ARCHIVE_MATERIAL, '伯乐免疫多项', '昆涞免疫多项'])
const materials = ref([])
const filterMaterial = ref('')
const filterMode = ref('')
const filterMethod = ref('')
const kw = ref('')

async function loadBatches() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterMaterial.value) params.qc_material = filterMaterial.value
    if (filterMode.value) params.mode = filterMode.value
    if (filterMethod.value) params.method = filterMethod.value
    if (kw.value) params.q = kw.value
    const res = await listTargetBatches(params)
    const data = res.items || res || []
    rows.value = data
    total.value = res.total || data.length
    // 拉取每个批号的录入次数与状态
    await Promise.all(rows.value.map(async (r) => {
      try {
        const d = await listTargetResults(r.id)
        r._entries = d.stats.total_entries
        r._status = d.stats.batch_status
      } catch (e) { r._entries = '—'; r._status = '—' }
    }))
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadMaterials()
  loadBatches()
})

async function loadMaterials() {
  try {
    const res = await listQcMaterials()
    materials.value = res || []
    presets.value = materials.value.map(m => m.name)
  } catch (e) {}
}

function statusType(s) {
  if (s === '已确立' || s === '在控' || s === '在控(人工)') return 'success'
  if (s === '警告' || s === '可暂定' || s === '可确立') return 'warning'
  if (s === '失控' || s === '有失控') return 'danger'
  return 'info'
}

// ---------------- 新建/编辑 ----------------
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ id: null, qc_material: '', qc_material_id: null, lot_no: '', level: 0, instrument: '', method: 'conventional', note: '' })
const archiveFile = ref(null)
const currentArchive = ref('')

const currentMatItems = computed(() => {
  if (!editForm.qc_material_id) return []
  const m = materials.value.find(x => x.id === editForm.qc_material_id)
  return m && m.items ? m.items : []
})

function onMaterialPick(id) {
  const m = materials.value.find(x => x.id === id)
  editForm.qc_material = m ? m.name : ''
  if (editForm.qc_material === ARCHIVE_MATERIAL) editForm.method = ''
}
function openNew() {
  Object.assign(editForm, { id: null, qc_material: '', qc_material_id: null, lot_no: '', level: 0, instrument: '', method: 'conventional', note: '' })
  archiveFile.value = null
  currentArchive.value = ''
  editVisible.value = true
}
function onArchivePick(e) {
  archiveFile.value = e.target.files[0] || null
}
async function saveBatch() {
  if (!editForm.qc_material || !editForm.lot_no) {
    ElMessage.warning('请填写质控品与批号')
    return
  }
  saving.value = true
  try {
    const payload = {
      qc_material: editForm.qc_material,
      qc_material_id: editForm.qc_material_id || null,
      lot_no: editForm.lot_no,
      level: Number(editForm.level) || 0,
      instrument: editForm.instrument,
      method: editForm.qc_material === ARCHIVE_MATERIAL ? '' : editForm.method,
      mode: editForm.qc_material === ARCHIVE_MATERIAL ? 'archive' : 'entry',
      note: editForm.note,
    }
    let id = editForm.id
    if (id) {
      await updateTargetBatch(id, payload)
    } else {
      const created = await createTargetBatch(payload)
      id = created.id
    }
    // 上传存档
    if (archiveFile.value) {
      await uploadTargetArchive(id, archiveFile.value)
    }
    ElMessage.success('已保存')
    editVisible.value = false
    loadBatches()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function removeBatch(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.qc_material} ${row.lot_no}」？`, '提示', { type: 'warning' })
  } catch (e) { return }
  try {
    await deleteTargetBatch(row.id)
    ElMessage.success('已删除')
    loadBatches()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

// ---------------- 质控品主数据管理 ----------------
const matManageVisible = ref(false)
const matEditVisible = ref(false)
const matLoading = ref(false)
const matSaving = ref(false)
const matForm = reactive({ id: null, name: '', note: '' })
const matItemsText = ref('')

function openMatManage() {
  loadMaterials()
  matManageVisible.value = true
}
function openMatNew() {
  Object.assign(matForm, { id: null, name: '', note: '' })
  matItemsText.value = ''
  matEditVisible.value = true
}
function openMatEdit(row) {
  Object.assign(matForm, { id: row.id, name: row.name, note: row.note || '' })
  matItemsText.value = (row.items || []).join('\n')
  matEditVisible.value = true
}
async function saveMat() {
  if (!matForm.name || !matForm.name.trim()) {
    ElMessage.warning('请填写质控品名称')
    return
  }
  matSaving.value = true
  try {
    const items = matItemsText.value.split('\n').map(s => s.trim()).filter(Boolean)
    const payload = { name: matForm.name.trim(), items, note: matForm.note }
    if (matForm.id) await updateQcMaterial(matForm.id, payload)
    else await createQcMaterial(payload)
    ElMessage.success('已保存')
    matEditVisible.value = false
    await loadMaterials()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    matSaving.value = false
  }
}
async function delMat(row) {
  try {
    await ElMessageBox.confirm(`确认删除质控品「${row.name}」？关联批号的项目预填将失效（批号本身保留）。`, '提示', { type: 'warning' })
  } catch (e) { return }
  try {
    await deleteQcMaterial(row.id)
    ElMessage.success('已删除')
    await loadMaterials()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

// ---------------- 详情/录入 ----------------
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailRow = ref(null)
const stats = reactive({ analytes: [], per_analyte: {}, batch_status: '', total_entries: 0, out_count: 0, established_analytes: 0 })
const resultRows = ref([])
const adding = ref(false)
const resultForm = reactive({ analyte: '', value: '', qc_date: '' })
const lastNote = ref('')
const lastNoteType = ref('info')
const archiveUrl = ref('')
const archSaving = ref(false)
const detailArchiveFile = ref(null)

async function openDetail(row) {
  detailRow.value = row
  detailVisible.value = true
  detailLoading.value = true
  lastNote.value = ''
  resultForm.analyte = ''
  resultForm.value = ''
  resultForm.qc_date = new Date().toISOString().slice(0, 10)
  try {
    if (row.mode === 'archive' && row.archive_filename) {
      await previewArchive(row, true)
    }
    await refreshDetail()
  } finally {
    detailLoading.value = false
  }
}

async function refreshDetail() {
  if (!detailRow.value) return
  const d = await listTargetResults(detailRow.value.id)
  resultRows.value = d.rows || []
  Object.assign(stats, d.stats)
}

async function submitResult() {
  if (!resultForm.analyte || resultForm.value === '' || resultForm.value === null) {
    ElMessage.warning('请填写项目与测定值')
    return
  }
  adding.value = true
  lastNote.value = ''
  try {
    const res = await addTargetResult(detailRow.value.id, {
      analyte: resultForm.analyte,
      value: Number(resultForm.value),
      qc_date: resultForm.qc_date,
    })
    await refreshDetail()
    // 即刻法：展示查表判定
    const a = resultForm.analyte
    const per = (res.stats?.per_analyte || {})[a] || {}
    const r = res.row || {}
    if (detailRow.value.method === 'immediate' && r.si_upper != null) {
      lastNote.value = `本次（n=${per.n}）：SI上限=${r.si_upper}，SI下限=${r.si_lower}；查表 2s=${per.n2s} 3s=${per.n3s} → ${r.status}`
      lastNoteType.value = r.status === '失控' ? 'error' : (r.status === '警告' ? 'warning' : 'success')
    } else if (per.manual) {
      lastNote.value = `该项目已有手动确认记录，新值直接纳入累计（跳过自动判定）`
      lastNoteType.value = 'success'
    } else if (detailRow.value.method === 'conventional' && per.n < 20 && per.n < 10) {
      lastNote.value = `已累计 ${per.n} 次（常规法需≥10可暂定、≥20确立）`
      lastNoteType.value = 'info'
    }
    resultForm.value = ''
  } catch (e) {
    ElMessage.error('录入失败：' + (e.response?.data?.detail || e.message))
  } finally {
    adding.value = false
  }
}

async function delRow(row) {
  try {
    await deleteTargetResult(detailRow.value.id, row.id)
    await refreshDetail()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}
async function toggleRow(row) {
  try {
    await toggleTargetResult(detailRow.value.id, row.id)
    await refreshDetail()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}
async function doEstablish() {
  try {
    await establishTarget(detailRow.value.id)
    ElMessage.success('已确立靶值')
    await refreshDetail()
  } catch (e) {
    ElMessage.error('确立失败：' + (e.response?.data?.detail || e.message))
  }
}
async function saveNote() {
  if (!detailRow.value) return
  try { await updateTargetBatch(detailRow.value.id, { note: detailRow.value.note }) } catch (e) {}
}

// ---------------- 存档预览 ----------------
async function previewArchive(row, forDetail = false) {
  if (!row.archive_filename) { ElMessage.warning('无存档文件'); return }
  try {
    const blob = await downloadTargetArchive(row.id)
    const url = URL.createObjectURL(blob)
    if (forDetail) {
      if (archiveUrl.value) URL.revokeObjectURL(archiveUrl.value)
      archiveUrl.value = url
    } else {
      const win = window.open(url, '_blank')
      if (!win) {
        const a = document.createElement('a')
        a.href = url; a.download = row.archive_filename; document.body.appendChild(a); a.click(); a.remove()
      }
      setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000)
    }
  } catch (e) {
    ElMessage.error('预览失败：' + (e.response?.data?.detail || e.message))
  }
}
function onDetailClose() {
  if (archiveUrl.value) { URL.revokeObjectURL(archiveUrl.value); archiveUrl.value = '' }
}
function onDetailArchivePick(e) {
  detailArchiveFile.value = e.target.files[0] || null
}
async function uploadDetailArchive() {
  if (!detailArchiveFile.value) { ElMessage.warning('请选择PDF'); return }
  archSaving.value = true
  try {
    await uploadTargetArchive(detailRow.value.id, detailArchiveFile.value)
    detailRow.value.archive_filename = detailArchiveFile.value.name
    await previewArchive(detailRow.value, true)
    ElMessage.success('已上传')
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    archSaving.value = false
  }
}
</script>

<style scoped>
.target-board { padding: 4px; }
.tb { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
.tb-hint { color: #909399; font-size: 12px; margin-left: 4px; }
.lv-muted { color: #c0c4cc; }
.pager { margin-top: 12px; display: flex; justify-content: center; }
.form-tip { color: #909399; font-size: 12px; margin-top: 4px; }
.file-tip { font-size: 12px; color: #606266; margin-top: 4px; }
.file-tip.muted { color: #909399; }
.d-info { display: flex; flex-wrap: wrap; gap: 16px; padding: 8px 0; font-size: 13px; color: #606266; align-items: center; }
.d-note { margin: 8px 0; }
.d-note-label { font-size: 13px; color: #606266; margin-bottom: 4px; }
.pdf-wrap { background: #f5f7fa; border-radius: 6px; overflow: hidden; }
.ana-cards { display: flex; flex-wrap: wrap; gap: 10px; margin: 8px 0; }
.ana-card { border: 1px solid #ebeef5; border-radius: 8px; padding: 10px 12px; min-width: 180px; background: #fafafa; }
.ana-name { font-weight: 600; margin-bottom: 6px; color: #1a365d; }
.ana-row { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
.ana-row b { color: #303133; }
.entry { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0; }
.mat-pick { display: flex; gap: 8px; align-items: center; width: 100%; }
.mat-toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
</style>
