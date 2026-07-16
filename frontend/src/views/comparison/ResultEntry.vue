<template>
  <el-dialog :model-value="visible" :title="`结果录入 · ${plan?.form_code || ''}`" width="1180px"
    top="3vh" @update:model-value="(v) => !v && $emit('close')">
    <div v-if="loading" v-loading="true" style="height:300px" />
    <template v-else>
      <el-alert v-if="category === '定量'" type="info" :closable="false" show-icon
        title="录入参照仪器与各比对仪器的检测值，偏倚%与是否允许自动计算。" style="margin-bottom:8px" />
      <el-alert v-else type="info" :closable="false" show-icon
        title="逐台仪器录入5例样本阴/阳性（P/N），符合率自动计算（以参照仪器为基准）。" style="margin-bottom:8px" />
      <el-alert v-if="plan?.only_uncompared" type="warning" :closable="false" show-icon
        title="本计划为同半年补录：仅列出本期尚未比对的项目，已做项目不显示。" style="margin-bottom:8px" />

      <div style="display:flex;gap:12px;margin-bottom:8px;align-items:center;flex-wrap:wrap">
        <el-switch v-model="showOnlyUnfinished" active-text="仅显示未完成" />
        <el-button size="small" :type="focusItem ? 'primary' : 'default'" @click="focusItem = null">
          全部项目{{ focusItem ? `（聚焦：${focusItem}）` : '' }}
        </el-button>
        <span style="color:#888;font-size:12px">共 {{ navItems.length }} 项，已完成 {{ doneCount }} 项</span>
      </div>

      <div style="display:flex;gap:12px">
        <!-- 左侧项目导航：点击聚焦，已完成打勾 -->
        <div style="width:170px;flex:none;border:1px solid #ebeef5;border-radius:6px;overflow:hidden">
          <div style="background:#f5f7fa;padding:6px 10px;font-size:12px;color:#666;border-bottom:1px solid #ebeef5">
            项目导航（点击聚焦）
          </div>
          <el-scrollbar style="height:420px">
            <div
              v-for="it in navItems" :key="it.name"
              @click="focusItem = (focusItem === it.name ? null : it.name)"
              :class="['nav-item', { active: focusItem === it.name, done: it.done }]"
            >
              <span class="nav-dot">{{ it.done ? '✓' : '○' }}</span>
              <span class="nav-name">{{ it.name }}</span>
            </div>
          </el-scrollbar>
        </div>

        <!-- 右侧录入区 -->
        <div style="flex:1;min-width:0">
          <!-- 定量 -->
          <template v-if="category === '定量'">
            <el-tabs v-model="currentLevel" type="card">
              <el-tab-pane v-for="lv in levels" :key="lv" :label="`水平${lv}`" :name="lv" />
            </el-tabs>
            <el-table :data="quantDisplay" size="small" border max-height="460">
              <el-table-column prop="item" label="项目" min-width="120" fixed />
              <el-table-column label="参照值" width="110">
                <template #default="{ row }">
                  <el-input v-model="row.reference_value" size="small" @input="onEdit" />
                </template>
              </el-table-column>
              <el-table-column v-for="ins in compared" :key="ins.id" :label="ins.name">
                <template #header>
                  <span>{{ ins.name }}</span>
                </template>
                <template #default="{ row }">
                  <div v-if="!isApplicable(row.item, ins.id)" class="masked" title="该项目不在此仪器上开展">/</div>
                  <div v-else style="display:flex;flex-direction:column;gap:2px">
                    <el-input v-model="row.values[ins.id]" size="small" placeholder="值" @input="onEdit" />
                    <div style="font-size:11px">
                      <span :class="biasOf(row, ins).ok === false ? 'no' : (biasOf(row, ins).ok ? 'yes' : '')">
                        偏倚 {{ fmt(biasOf(row, ins).bias) }}%
                      </span>
                      <span :class="biasOf(row, ins).ok === false ? 'no' : (biasOf(row, ins).ok ? 'yes' : '')">
                        {{ biasOf(row, ins).ok === false ? '✗' : (biasOf(row, ins).ok ? '✓' : '-') }}
                      </span>
                    </div>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <!-- 定性 -->
          <template v-else>
            <el-table :data="qualDisplay" size="small" border max-height="460">
              <el-table-column prop="item" label="项目" min-width="140" fixed />
              <el-table-column v-for="ins in allInstruments" :key="ins.id" :label="ins.name + (ins.is_reference ? '（参照）' : '')">
                <template #default="{ row }">
                  <div v-if="!isApplicable(row.item, ins.id)" class="masked" title="该项目不在此仪器上开展">/</div>
                  <template v-else>
                    <div style="display:flex;gap:3px;flex-wrap:wrap">
                      <el-select v-for="k in 5" :key="k" v-model="row.results[ins.id][k - 1]" size="small"
                        style="width:58px" @change="onEdit">
                        <el-option label="P" value="P" />
                        <el-option label="N" value="N" />
                      </el-select>
                    </div>
                    <div style="font-size:11px" :class="agreementOf(row, ins).ok === false ? 'no' : (agreementOf(row, ins).ok ? 'yes' : '')">
                      符合率 {{ agreementOf(row, ins).val == null ? '-' : agreementOf(row, ins).val + '%' }}
                    </div>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </div>
      </div>
    </template>
    <template #footer>
      <el-upload v-if="category === '定量'" :show-file-list="false" accept=".xlsx,.xls"
        :before-upload="onImportFile" style="display:inline-block;margin-right:8px">
        <el-button :loading="importing">从Excel导入</el-button>
      </el-upload>
      <el-button @click="$emit('close')">关闭</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存结果</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getResults, saveResults, importResults, getUncompared } from '../../api/comparison'

const props = defineProps({
  visible: Boolean,
  plan: { type: Object, default: null },
  group: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const category = ref('定量')
const levels = ref(5)
const allInstruments = ref([])
const itemMeta = ref({}) // name -> {te, mode}
const quantRows = ref([]) // {item, level, reference_value, values:{id:val}}
const qualRows = ref([]) // {item, results:{id:[5]}}
const currentLevel = ref(1)
const dirty = ref(false)

// 便捷性增强
const showOnlyUnfinished = ref(false)
const focusItem = ref(null)
const savedItems = ref(new Set())   // 本计划已录入结果的项目名
const allItemNames = ref([])        // 分组全量项目名
const scopeItems = ref(null)        // plan.only_uncompared 时=本期未比对项目名；否则 null(全量)

const compared = computed(() => allInstruments.value.filter((i) => !i.is_reference))

const isDone = (name) => savedItems.value.has(name)
const scopeSet = computed(() => (scopeItems.value ? new Set(scopeItems.value) : null))

// 导航项：优先用本期未比对范围；按"仅显示未完成"过滤
const navItems = computed(() => {
  const base = scopeItems.value || allItemNames.value
  return base.map((name) => ({ name, done: isDone(name) }))
    .filter((it) => !showOnlyUnfinished.value || !it.done)
})
const doneCount = computed(() => navItems.value.filter((i) => i.done).length)

const currentRows = computed(() => quantRows.value.filter((r) => r.level === currentLevel.value))
function _passScope(item) {
  if (scopeSet.value && !scopeSet.value.has(item)) return false
  if (showOnlyUnfinished.value && isDone(item)) return false
  if (focusItem.value && focusItem.value !== item) return false
  return true
}
const quantDisplay = computed(() => currentRows.value.filter((r) => _passScope(r.item)))
const qualDisplay = computed(() => qualRows.value.filter((r) => _passScope(r.item)))

function onEdit() { dirty.value = true }

function biasOf(row, ins) {
  const meta = itemMeta.value[row.item] || { te: '0', mode: 'relative' }
  const rf = parseFloat(row.reference_value)
  const vf = parseFloat(row.values[ins.id])
  const tf = parseFloat(meta.te)
  if (isNaN(rf) || isNaN(vf) || isNaN(tf)) return { bias: null, ok: null }
  let b = meta.mode === 'absolute' ? vf - rf : (rf === 0 ? null : (vf - rf) / rf * 100)
  if (b === null) return { bias: null, ok: null }
  return { bias: Math.round(b * 100) / 100, ok: Math.abs(b) <= tf + 1e-9 }
}
function agreementOf(row, ins) {
  const ref = allInstruments.value.find((i) => i.is_reference)
  const r = ref ? row.results[ref.id] : null
  const v = row.results[ins.id]
  if (!r || !v || r.length !== v.length) return { val: null, ok: null }
  const valid = v.filter((x) => x === 'P' || x === 'N').length
  const matches = v.filter((x, i) => x === r[i] && (x === 'P' || x === 'N')).length
  if (!valid) return { val: null, ok: null }
  const pct = Math.round((matches / valid) * 1000) / 10
  return { val: pct, ok: pct >= 80 }
}
function fmt(x) { return x == null ? '-' : x }

// 遮蔽：项目 meta.instrument_ids 非空且不含该仪器 → 不适用（录入遮蔽）
function isApplicable(item, insId) {
  const meta = itemMeta.value[item]
  const ids = meta && meta.instrument_ids
  if (!ids || !ids.length) return true // 空=组内全部适用
  return ids.includes(insId)
}

// 对话框以 v-if 挂载，挂载时 props.visible 已为 true；用 immediate 确保挂载即加载，
// 避免「打开录入对话框却是空白、无法录入」的问题。
watch(() => props.visible, async (v) => {
  if (!v || !props.plan) return
  await load()
}, { immediate: true })
async function load() {
  loading.value = true
  focusItem.value = null
  try {
    const data = await getResults(props.plan.id)
    category.value = data.category
    levels.value = data.levels
    allInstruments.value = data.instruments
    itemMeta.value = {}
    data.items.forEach((i) => { itemMeta.value[i.name] = i })
    allItemNames.value = data.items.map((i) => i.name)
    currentLevel.value = 1
    // 已录入结果的项目（用于"已完成"标记）
    const done = new Set()
    data.quant.forEach((r) => { if (r.reference_value || (r.values && Object.values(r.values).some((v) => v !== '' && v != null))) done.add(r.item) })
    data.qual.forEach((r) => { if (r.results && Object.values(r.results).some((arr) => Array.isArray(arr) && arr.some((x) => x))) done.add(r.item) })
    savedItems.value = done
    // 同半年补录：拉取本期未比对项目作为范围
    if (props.plan.only_uncompared && props.group) {
      try {
        const res = await getUncompared(props.group.id, {
          year: props.plan.year, half: props.plan.half, exclude_plan_id: props.plan.id,
        })
        scopeItems.value = res.uncompared || []
      } catch (e) {
        scopeItems.value = null
      }
    } else {
      scopeItems.value = null
    }
    showOnlyUnfinished.value = !!props.plan.only_uncompared
    // 定量：补齐 项目×水平
    const qmap = {}
    data.quant.forEach((r) => { qmap[`${r.item}__${r.level}`] = r })
    const qr = []
    for (let lv = 1; lv <= data.levels; lv++) {
      data.items.forEach((it) => {
        const ex = qmap[`${it.name}__${lv}`]
        qr.push({
          item: it.name, level: lv,
          reference_value: ex ? ex.reference_value : '',
          values: ex ? { ...ex.values } : {},
        })
      })
    }
    quantRows.value = qr
    // 定性：补齐 项目
    const qualmap = {}
    data.qual.forEach((r) => { qualmap[r.item] = r })
    qualRows.value = data.items.map((it) => {
      const ex = qualmap[it.name]
      const results = {}
      allInstruments.value.forEach((ins) => {
        results[ins.id] = (ex && ex.results && ex.results[ins.id]) ? [...ex.results[ins.id]] : Array(5).fill('')
      })
      return { item: it.name, results }
    })
    dirty.value = false
  } catch (e) {
    ElMessage.error('加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function onImportFile(file) {
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await importResults(props.plan.id, fd)
    const matched = res.matched_items?.length || 0
    const unmatched = res.unmatched_items?.length || 0
    if (unmatched > 0) {
      ElMessage.warning(
        `已导入 ${res.imported} 条结果（${matched} 个项目）；未能匹配项目：${res.unmatched_items.join('、')}`)
    } else {
      ElMessage.success(`已导入 ${res.imported} 条结果（${matched} 个项目，水平 ${res.levels}）`)
    }
    await load()
    emit('saved')
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || e.message))
  } finally {
    importing.value = false
  }
  return false // 阻止 el-upload 自动上传（我们手动发请求）
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      quant: quantRows.value.map((r) => {
        // 遮蔽仪器不保存数值
        const values = {}
        Object.keys(r.values || {}).forEach((k) => {
          if (isApplicable(r.item, Number(k))) values[k] = r.values[k]
        })
        return { item: r.item, level: r.level, reference_value: r.reference_value, values }
      }),
      qual: qualRows.value.map((r) => {
        const results = {}
        Object.keys(r.results || {}).forEach((k) => {
          if (isApplicable(r.item, Number(k))) results[k] = r.results[k]
        })
        return { item: r.item, results }
      }),
    }
    await saveResults(props.plan.id, payload)
    ElMessage.success('结果已保存')
    dirty.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.yes { color: #27ae60; font-weight: 700; }
.no { color: #c0392b; font-weight: 700; }
.masked {
  text-align: center; color: #bbb; font-size: 16px; font-weight: 700;
  background: #f5f5f5; border-radius: 4px; padding: 6px 0; user-select: none;
}
.nav-item {
  display: flex; align-items: center; gap: 6px; padding: 6px 10px; cursor: pointer;
  font-size: 13px; border-bottom: 1px solid #f5f5f5;
}
.nav-item:hover { background: #f0f7ff; }
.nav-item.active { background: #e6f0ff; font-weight: 700; }
.nav-item.done { color: #27ae60; }
.nav-dot { width: 16px; text-align: center; }
.nav-name { flex: 1; }
</style>
