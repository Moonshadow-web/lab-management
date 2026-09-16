<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">试剂验收</h2>
      <p class="sub">
        试剂 / 质控品更换批号时的批间性能验证：同一项目用旧、新批号各测 {{ defaultSampleCount }} 个样本（可选质控品 + 患者样本），
        计算相对偏倚；<b>{{ defaultSampleCount }} 个中 ≥ {{ defaultSampleCount - 1 }} 个相对偏倚 ≤ 允许偏倚</b> 判定为符合要求。
      </p>
    </div>
    <LibraryTabs @change="refresh" />

    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索试剂名/批号/项目..." clearable style="width:240px"
        @keyup.enter="refresh" @clear="refresh">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width:120px" @change="refresh">
        <el-option label="待验证" value="待验证" />
        <el-option label="已完成" value="已完成" />
      </el-select>
      <el-select v-model="filterConclusion" placeholder="全部结论" clearable style="width:130px" @change="refresh">
        <el-option label="待完成" value="待完成" />
        <el-option label="符合要求" value="符合要求" />
        <el-option label="不符合要求" value="不符合要求" />
      </el-select>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
      <el-button v-if="canWrite" type="primary" :icon="Plus" @click="onNew">新建验收</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" border stripe height="calc(100vh - 390px)">
      <el-table-column type="index" width="50" />
      <el-table-column label="试剂 / 质控品" min-width="200">
        <template #default="{ row }">
          <div>{{ row.reagent_name }}</div>
          <div class="muted2">{{ row.spec }}<span v-if="row.brand"> · {{ row.brand }}</span></div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="80">
        <template #default="{ row }"><el-tag size="small" :type="row.item_type === '质控品' ? 'warning' : 'info'">{{ row.item_type }}</el-tag></template>
      </el-table-column>
      <el-table-column label="批号变更" width="230">
        <template #default="{ row }">
          <div style="font-size:12px">
            <span class="muted2">旧</span> {{ row.old_batch_no || '—' }}
            <span class="arrow">→</span>
            <span class="muted2">新</span> <b>{{ row.new_batch_no || '—' }}</b>
          </div>
          <div class="muted2" style="font-size:11px">变更日期：{{ row.change_date || '—' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="效期（新批号）" width="120">
        <template #default="{ row }">{{ row.new_expiry_date || '—' }}</template>
      </el-table-column>
      <el-table-column prop="test_item_name" label="检验项目" width="150">
        <template #default="{ row }">{{ row.test_item_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="允许偏倚" width="150">
        <template #default="{ row }">
          <div v-if="row.allow_bias_pct"><b>{{ row.allow_bias_pct }}%</b></div>
          <div class="muted2" style="font-size:11px">{{ row.criterion_label || '手工填写' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="合格/总数" width="90" align="center">
        <template #default="{ row }">{{ row.pass_count }} / {{ row.sample_count }}</template>
      </el-table-column>
      <el-table-column label="结论" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.conclusion)">{{ row.conclusion }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="操作人" width="90" />
      <el-table-column label="操作" width="180" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onEdit(row)">录入</el-button>
          <el-button size="small" link type="primary" @click="onPrint(row)">打印</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20,50,100]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 录入弹窗 -->
    <el-dialog v-model="dlgVisible" :title="editing ? '试剂批间性能验证' : '新建试剂验收'" width="min(900px, 96vw)" top="3vh">
      <el-form :model="form" label-width="92px" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="试剂">
              <el-select v-model="form.item_id" filterable placeholder="选择试剂" style="width:100%"
                :disabled="!!editing" @change="onPickReagent">
                <el-option v-for="it in reagentItems" :key="it.id" :label="it.name" :value="it.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检验项目">
              <el-select v-model="form.test_item_id" filterable clearable
                :placeholder="prep.test_items.length ? '自动关联（可改）' : '选择项目（用于取允许偏倚）'"
                style="width:100%" @change="onPickTestItem">
                <el-option v-for="t in (prep.test_items.length ? prep.test_items : testItems)"
                  :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
              <div v-if="prep.test_items.length" class="muted2" style="font-size:11px">
                自动关联 {{ prep.test_items.length }} 个项目
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="旧批号">
              <el-select v-model="form.old_batch_no" filterable allow-create default-first-option
                placeholder="库存当前批次" style="width:100%" @change="onPickOldBatch">
                <el-option v-for="b in prep.stock_batches" :key="b.batch_no"
                  :label="b.batch_no + '（库存 ' + b.quantity + '）'" :value="b.batch_no" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="新批号">
              <el-select v-model="form.new_batch_no" filterable allow-create default-first-option
                placeholder="最近到货批次" style="width:100%" @change="onPickNewBatch">
                <el-option v-for="c in prep.new_batch_candidates" :key="c.batch_no"
                  :label="c.batch_no + (c.already_in_stock ? '（已在库）' : '') + (c.receipt_date ? ' ' + c.receipt_date : '')"
                  :value="c.batch_no" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="变更日期">
              <el-date-picker v-model="form.change_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="新批号效期">
              <el-date-picker v-model="form.new_expiry_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="允许偏倚%">
              <el-input v-model="form.allow_bias_pct" placeholder="自动带出，可改" style="width:120px" />
              <el-button v-if="form.item_id" size="small" style="margin-left:8px" @click="reloadCriteria">重新取标准</el-button>
            </el-form-item>
          </el-col>
          <el-col :span="14">
            <el-form-item label="判定标准">
              <span class="muted2">{{ form.criterion_label || '—' }}</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="samples-title">
        <span>比对样本（旧批号 vs 新批号）</span>
        <el-button size="small" :icon="Plus" @click="addSample">加一行</el-button>
        <el-button size="small" @click="resetSamples">重置为 {{ form.sample_count }} 行</el-button>
      </div>
      <el-table :data="form.samples" border size="small">
        <el-table-column type="index" width="46" />
        <el-table-column label="样本名称" min-width="130">
          <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-select v-model="row.kind" size="small">
              <el-option label="质控" value="质控" />
              <el-option label="样本" value="样本" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="旧批号结果" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.old_value" :controls="false" size="small" style="width:110px" />
          </template>
        </el-table-column>
        <el-table-column label="新批号结果" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.new_value" :controls="false" size="small" style="width:110px" />
          </template>
        </el-table-column>
        <el-table-column label="相对偏倚%" width="110" align="center">
          <template #default="{ row }">
            <span :class="biasCls(row)">{{ biasOf(row) === null ? '—' : biasOf(row) + '%' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="是否合格" width="90" align="center">
          <template #default="{ row }">
            <span v-if="passOf(row) === null" class="muted2">—</span>
            <el-tag v-else size="small" :type="passOf(row) ? 'success' : 'danger'">{{ passOf(row) ? '合格' : '不合格' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="" width="60">
          <template #default="{ $index }">
            <el-button size="small" link type="danger" @click="form.samples.splice($index, 1)">删</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="conclusion">
        <span>合格 <b>{{ localPass }}</b> / {{ form.samples.length }} 个</span>
        <el-tag :type="tagType(localConclusion)" style="margin-left:12px">{{ localConclusion }}</el-tag>
        <span class="muted2" style="margin-left:12px;font-size:12px">
          判定：相对偏倚绝对值 ≤ 允许偏倚，且合格数 ≥ {{ Math.max(1, form.samples.length - 1) }}
        </span>
      </div>
      <el-form size="small" label-width="92px" style="margin-top:10px">
        <el-form-item label="操作人"><el-input v-model="form.operator" style="width:160px" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import {
  listLotVerifications, createLotVerification, updateLotVerification,
  deleteLotVerification, getLotCriteria, prepareLotVerification,
} from '../../api/reagent'
import { listAllReagentItems } from '../../api/reagent'
import request from '../../utils/request'
import { useAuthStore } from '../../store/auth'
import { useReagentStore } from '../../store/reagent'
import { errText } from '../../utils/errText'
import { printHtml } from '../../utils/printHtml'
import LibraryTabs from '../../components/reagent/LibraryTabs.vue'

const auth = useAuthStore()
const reagentStore = useReagentStore()
const canWrite = computed(() => auth.isAdmin || auth.canWrite('reagents'))
const defaultSampleCount = 5

const rows = ref([]), total = ref(0), page = ref(1), pageSize = ref(20), loading = ref(false)
const q = ref(''), filterStatus = ref(''), filterConclusion = ref('')
const dlgVisible = ref(false), saving = ref(false), editing = ref(null)
const reagentItems = ref([]), testItems = ref([])

const FOOT = '表格编号：BG-SM-CZ-029　　民航总医院检验科生化免疫组　　生效日期：2026.9.1'
const DOC_TITLE = '生化免疫组试剂批间性能验证平行试验记录表'

const emptyForm = () => ({
  item_id: null, library: '', item_type: '试剂', reagent_name: '', spec: '', brand: '',
  old_batch_no: '', old_expiry_date: null, new_batch_no: '', new_expiry_date: null,
  change_date: null, test_item_id: null, test_item_name: '',
  criterion_source: '', criterion_label: '', allow_bias_pct: '',
  samples: [], sample_count: defaultSampleCount, operator: '', remark: '',
})
const form = reactive(emptyForm())

function mkSamples(n) {
  return Array.from({ length: n }, (_, i) => ({
    name: `样本${i + 1}`, kind: '样本', old_value: null, new_value: null,
  }))
}

function biasOf(r) {
  const ov = r.old_value, nv = r.new_value
  if (ov === null || ov === undefined || nv === null || nv === undefined) return null
  if (Math.abs(Number(ov)) < 1e-12) return null
  return Math.round(((Number(nv) - Number(ov)) / Math.abs(Number(ov))) * 10000) / 100
}
function passOf(r) {
  const b = biasOf(r)
  const allow = parseFloat(form.allow_bias_pct)
  if (b === null || !allow) return null
  return Math.abs(b) <= allow + 1e-9
}
function biasCls(r) {
  const p = passOf(r)
  if (p === null) return ''
  return p ? 'ok' : 'bad'
}
const localPass = computed(() => form.samples.filter(r => passOf(r) === true).length)
const validCount = computed(() => form.samples.filter(r => biasOf(r) !== null).length)
const localConclusion = computed(() => {
  const allow = parseFloat(form.allow_bias_pct)
  if (!allow) return '待完成'
  const total = form.samples.length
  const need = Math.max(1, total - 1)
  if (validCount.value === 0) return '待完成'          // 还没录结果
  if (localPass.value >= need) return '符合要求'
  if (total > 0 && validCount.value >= total) return '不符合要求'  // 全录完仍不达标
  return '待完成'                                      // 只录了一部分
})

function tagType(c) {
  return c === '符合要求' ? 'success' : c === '不符合要求' ? 'danger' : 'info'
}

async function refresh() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value, library: reagentStore.library }
    if (q.value.trim()) params.q = q.value.trim()
    if (filterStatus.value) params.status = filterStatus.value
    if (filterConclusion.value) params.conclusion = filterConclusion.value
    const r = await listLotVerifications(params)
    rows.value = r.items; total.value = r.total
  } catch (e) { ElMessage.error('加载失败：' + errText(e)) } finally { loading.value = false }
}

async function ensureOptions() {
  if (!reagentItems.value.length) {
    const all = await listAllReagentItems({})
    reagentItems.value = (all || []).filter(i => i.type === '试剂' || i.type === '质控品')
  }
  if (!testItems.value.length) {
    try {
      const r = await request.get('/api/v1/test-items', { params: { page: 1, page_size: 1000 } })
      testItems.value = r.items || []
    } catch (_) { testItems.value = [] }
  }
}

const prep = reactive({ test_items: [], stock_batches: [], new_batch_candidates: [] })

async function onPickReagent(id) {
  const it = reagentItems.value.find(i => i.id === id)
  if (it) {
    form.reagent_name = it.name; form.spec = it.spec || ''
    form.brand = it.brand || ''; form.item_type = it.type || '试剂'
    form.library = it.library || ''
  }
  // 一次调用把「关联项目 / 库存批号 / 到货批号 / 允许偏倚」全部带出来
  try {
    const d = await prepareLotVerification(id)
    prep.test_items = d.test_items || []
    prep.stock_batches = d.stock_batches || []
    prep.new_batch_candidates = d.new_batch_candidates || []
    if (!d.in_scope) {
      ElMessage.warning(d.exclude_reason || '该物品不在试剂批间验证范围')
    }
    // 自动关联项目（一个试剂可能对应多个项目，取第一个，仍可改）
    if (!form.test_item_name && prep.test_items.length) {
      form.test_item_id = prep.test_items[0].id
      form.test_item_name = prep.test_items[0].name
    }
    // 旧批号自动取库存当前批次
    if (!form.old_batch_no && d.old_batch) {
      form.old_batch_no = d.old_batch.batch_no
      form.old_expiry_date = d.old_batch.expiry_date || null
    }
    // 新批号若尚空，取「最近到货且不在库存中」的批号
    if (!form.new_batch_no) {
      const cand = prep.new_batch_candidates.find(c => !c.already_in_stock)
        || prep.new_batch_candidates[0]
      if (cand) {
        form.new_batch_no = cand.batch_no
        form.new_expiry_date = cand.expiry_date || null
        if (!form.change_date) form.change_date = cand.receipt_date || form.change_date
      }
    }
    if (d.allow_bias && d.allow_bias.pct > 0) {
      form.criterion_source = d.allow_bias.source
      form.criterion_label = d.allow_bias.label
      form.allow_bias_pct = String(d.allow_bias.pct)
    } else if (!form.allow_bias_pct) {
      ElMessage.info('未匹配到行标/卫健委标准，请手工填写允许偏倚')
    }
  } catch (e) { ElMessage.error('带出试剂信息失败：' + errText(e)) }
}
function onPickTestItem(id) {
  const t = testItems.value.find(i => i.id === id)
  form.test_item_name = t ? t.name : ''
  reloadCriteria()
}
function onPickNewBatch(b) {
  const c = prep.new_batch_candidates.find(x => x.batch_no === b)
  if (c) {
    form.new_expiry_date = c.expiry_date || null
    if (!form.change_date) form.change_date = c.receipt_date || form.change_date
  }
}
function onPickOldBatch(b) {
  const c = prep.stock_batches.find(x => x.batch_no === b)
  if (c) form.old_expiry_date = c.expiry_date || null
}
async function reloadCriteria() {
  if (!form.item_id) return
  try {
    const r = await getLotCriteria(form.item_id, form.test_item_name || '')
    if (r && r.pct > 0) {
      form.criterion_source = r.source
      form.criterion_label = r.label
      form.allow_bias_pct = String(r.pct)
    } else if (!form.allow_bias_pct) {
      ElMessage.info('未匹配到行标/卫健委标准，请手工填写允许偏倚')
    }
  } catch (e) { /* 静默 */ }
}

function addSample() { form.samples.push({ name: `样本${form.samples.length + 1}`, kind: '样本', old_value: null, new_value: null }) }
function resetSamples() { form.samples = mkSamples(form.sample_count || defaultSampleCount) }

async function onNew() {
  await ensureOptions()
  Object.assign(form, emptyForm())
  form.change_date = new Date().toISOString().slice(0, 10)
  form.operator = auth.user?.full_name || auth.user?.username || ''
  form.library = reagentStore.library || ''
  form.samples = mkSamples(defaultSampleCount)
  editing.value = null
  dlgVisible.value = true
}

async function onEdit(row) {
  await ensureOptions()
  Object.assign(form, emptyForm(), JSON.parse(JSON.stringify(row)))
  if (!form.samples || !form.samples.length) form.samples = mkSamples(form.sample_count || defaultSampleCount)
  if (!form.operator) form.operator = auth.user?.full_name || auth.user?.username || ''
  editing.value = row
  dlgVisible.value = true
}

async function onSave() {
  if (!form.item_id) { ElMessage.warning('请选择试剂'); return }
  saving.value = true
  try {
    const payload = {
      item_id: form.item_id, library: form.library, item_type: form.item_type,
      reagent_name: form.reagent_name, spec: form.spec, brand: form.brand,
      old_batch_no: form.old_batch_no, old_expiry_date: form.old_expiry_date || null,
      new_batch_no: form.new_batch_no, new_expiry_date: form.new_expiry_date || null,
      change_date: form.change_date || null,
      test_item_id: form.test_item_id, test_item_name: form.test_item_name,
      criterion_source: form.criterion_source, criterion_label: form.criterion_label,
      allow_bias_pct: form.allow_bias_pct,
      samples: form.samples.map(s => ({
        name: s.name, kind: s.kind,
        old_value: s.old_value === '' ? null : s.old_value,
        new_value: s.new_value === '' ? null : s.new_value,
      })),
      sample_count: form.samples.length,
      operator: form.operator, remark: form.remark,
    }
    if (editing.value) await updateLotVerification(editing.value.id, payload)
    else await createLotVerification(payload)
    ElMessage.success('已保存')
    dlgVisible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败：' + errText(e)) } finally { saving.value = false }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.reagent_name} ${row.old_batch_no}→${row.new_batch_no}」的验收记录？`, '删除', { type: 'warning' })
  } catch (_) { return }
  try {
    await deleteLotVerification(row.id)
    ElMessage.success('已删除'); refresh()
  } catch (e) { ElMessage.error('删除失败：' + errText(e)) }
}

function onPrint(row) {
  const samples = row.samples || []
  const allow = row.allow_bias_pct || '—'
  let h = '<table><thead><tr><th>序号</th><th>样本名称</th><th>类型</th>'
    + '<th class="num">旧批号结果</th><th class="num">新批号结果</th>'
    + '<th class="num">相对偏倚%</th><th class="num">是否合格</th></tr></thead><tbody>'
  samples.forEach((s, i) => {
    const b = s.bias_pct
    const ok = s.passed
    h += `<tr><td class="num">${i + 1}</td><td>${s.name || ''}</td><td>${s.kind || ''}</td>`
      + `<td class="num">${s.old_value ?? ''}</td><td class="num">${s.new_value ?? ''}</td>`
      + `<td class="num">${b === null || b === undefined ? '' : b}</td>`
      + `<td class="num">${ok === null || ok === undefined ? '' : (ok ? '合格' : '不合格')}</td></tr>`
  })
  h += '</tbody></table>'
  const meta = `试剂：${row.reagent_name}　规格：${row.spec || ''}　品牌：${row.brand || ''}<br>`
    + `批号变更：${row.old_batch_no || '—'} → <b>${row.new_batch_no || '—'}</b>　变更日期：${row.change_date || '—'}`
    + `　新批号效期：${row.new_expiry_date || '—'}<br>`
    + `检验项目：${row.test_item_name || '—'}　允许偏倚：<b>${allow}%</b>　`
    + `标准：${row.criterion_label || '手工填写'}<br>`
    + `结论：<b>${row.conclusion}</b>（合格 ${row.pass_count} / ${row.sample_count}）　操作人：${row.operator || ''}`
  printHtml(`${DOC_TITLE} ${row.reagent_name}`,
    `<table class="doc"><thead><tr><td><h2>${DOC_TITLE}</h2><div class="meta">${meta}</div></td></tr></thead>`
    + `<tbody><tr><td>${h}</td></tr></tbody>`
    + `<tfoot><tr><td><div class="doc-foot">${FOOT}</div></td></tr></tfoot></table>`)
}

onMounted(refresh)
</script>

<style scoped>
.page { padding: 16px 20px 0; display: flex; flex-direction: column; height: 100%; }
.page-header { margin-bottom: 8px; }
.title { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0; color: #64748b; font-size: 13px; line-height: 1.7; }
.toolbar { display: flex; gap: 10px; align-items: center; margin: 8px 0 12px; flex-wrap: wrap; }
.pager { margin: 10px 0 16px; display: flex; justify-content: flex-end; }
.muted2 { color: #94a3b8; font-size: 12px; }
.arrow { color: #2563eb; margin: 0 4px; }
.samples-title { display: flex; align-items: center; gap: 10px; margin: 6px 0 8px; font-size: 14px; font-weight: 600; }
.conclusion { margin-top: 12px; padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; }
.ok { color: #16a34a; font-weight: 600; }
.bad { color: #dc2626; font-weight: 600; }
</style>
