<template>
  <div class="pre-job-auth">
    <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
      <el-button size="small" type="primary" plain @click="showQrPublic">理论答题二维码（通用·免登录）</el-button>
    </div>
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索申请人"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button v-if="row.conclusion === '同意上岗' && !row.batch_id" link type="warning" @click="genAuths(row)">生成授权</el-button>
        <el-button v-if="row.batch_id" link type="success" @click="viewAuths(row)">查看授权</el-button>
        <el-button link type="primary" @click="showQr(row)">扫码答题</el-button>
        <el-button link type="primary" @click="printForm(row)">打印</el-button>
      </template>
    </CrudTable>

    <el-dialog v-model="visible" :title="form.id ? '编辑岗前培训考核及授权表' : '新增岗前培训考核及授权表'" width="880px" top="3vh">
      <el-form :model="form" label-width="130px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="申请人"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="申请日期"><el-input v-model="form.apply_date" placeholder="如 2026-09-09" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="考核岗位（多选）">
          <el-select v-model="positions" multiple style="width:100%" placeholder="按 GL-070 选择岗位，仪器自动带出">
            <el-option v-for="p in POSITIONS" :key="p.name" :label="p.name" :value="p.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="考核仪器（自动带出，可调整）">
          <el-select v-model="instrumentCodes" multiple style="width:100%">
            <el-option v-for="i in instrumentOptions" :key="i.code" :label="i.name + '（' + i.code.replace('MHZYY-JYK-', '') + '）'" :value="i.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="仪器关联项目（自动）">
          <div v-if="projLoading" style="color:#999;font-size:12px;">项目加载中…</div>
          <div v-for="r in instrumentProjects" :key="r.code" style="margin-bottom:6px;">
            <b style="font-size:12px;">{{ r.name }}：</b>
            <span style="font-size:12px;color:#444;">{{ r.projects || '（该仪器未关联项目）' }}</span>
          </div>
        </el-form-item>
        <el-form-item label="授权权限（多选）">
          <el-select v-model="permissions" multiple style="width:100%" placeholder="操作 / 复核 / 报告">
            <el-option v-for="s in AUTH_SCOPES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">按岗位考核（方式与题库自动带出，可填写）</el-divider>
        <el-button size="small" @click="autoJudge()" type="warning" style="margin-bottom:8px;">按考核结果自动判定考核意见</el-button>
        <div v-for="pc in examAreas" :key="pc.post" style="border:1px solid #e4e7ed;border-radius:6px;padding:10px 12px;margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <b style="font-size:15px;">{{ pc.post }}</b>
            <el-tag size="small" type="info">{{ pc.methods.join(' / ') }}</el-tag>
          </div>
          <el-row :gutter="8" style="margin-bottom:8px;">
            <el-col :span="6"><el-input v-model="examData[pc.post].trainTime" size="small" placeholder="培训时间" /></el-col>
            <el-col :span="6"><el-input v-model="examData[pc.post].trainPerson" size="small" placeholder="培训人" /></el-col>
            <el-col :span="12"><el-input v-model="examData[pc.post].trainContent" size="small" placeholder="培训内容" /></el-col>
          </el-row>

          <template v-if="pc.methods.includes('口头问答')">
            <div style="font-weight:600;margin:4px 0;">口头问答（题库问题，考官据此提问）</div>
            <div v-for="(qa, qi) in pc.bank.qa_json || []" :key="'q' + qi" style="margin-bottom:6px;">
              <div style="font-size:13px;">{{ qi + 1 }}. {{ qa.q }}</div>
            </div>
            <el-form-item label="考核结果" label-width="90px">
              <el-select v-model="examData[pc.post].qaResult" style="width:160px;"><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select>
            </el-form-item>
          </template>

          <template v-if="pc.methods.includes('实操考核')">
            <div style="font-weight:600;margin:4px 0;">实操考核（要点打分，满分 {{ pc.practicalTotal }}）</div>
            <div v-for="(pt, pi) in pc.bank.practical_json || []" :key="'p' + pi" style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <span style="flex:1;">{{ pi + 1 }}. {{ pt.point }}</span>
              <span style="color:#888;">满分 {{ pt.score }}</span>
              <el-input-number v-model="examData[pc.post].practicalScores[pi]" size="small" :min="0" :max="pt.score" style="width:110px;" />
            </div>
            <div>实操得分：<b>{{ practicalPct(pc) }}</b> / 100 分（合格线 80）</div>
          </template>

          <template v-if="pc.methods.includes('理论考核')">
            <div style="font-weight:600;margin:4px 0;">理论考核（单选/多选/判断各5题，自动判分）</div>
            <div v-for="(t, ti) in (pc.bank.theory_json && pc.bank.theory_json.single) || []" :key="'s' + ti" style="margin-bottom:4px;">
              <div>单选 {{ ti + 1 }}. {{ t.q }}</div>
              <el-radio-group v-model="examData[pc.post].theoryAnswers['s' + ti]" size="small">
                <el-radio v-for="o in t.options" :key="o" :value="o.slice(0, 1)">{{ o }}</el-radio>
              </el-radio-group>
            </div>
            <div v-for="(t, ti) in (pc.bank.theory_json && pc.bank.theory_json.multi) || []" :key="'m' + ti" style="margin-bottom:4px;">
              <div>多选 {{ ti + 1 }}. {{ t.q }}</div>
              <el-checkbox-group v-model="examData[pc.post].theoryAnswers['m' + ti]">
                <el-checkbox v-for="o in t.options" :key="o" :value="o.slice(0, 1)">{{ o }}</el-checkbox>
              </el-checkbox-group>
            </div>
            <div v-for="(t, ti) in (pc.bank.theory_json && pc.bank.theory_json.judge) || []" :key="'j' + ti" style="margin-bottom:4px;">
              <div>判断 {{ ti + 1 }}. {{ t.q }}</div>
              <el-radio-group v-model="examData[pc.post].theoryAnswers['j' + ti]" size="small">
                <el-radio value="对">对</el-radio><el-radio value="错">错</el-radio>
              </el-radio-group>
            </div>
            <div>理论得分：<b>{{ theoryPct(pc) }}</b> / 100 分（合格线 60）</div>
          </template>

          <el-form-item label="掌握程度" label-width="90px" style="margin-top:8px;">
            <el-radio-group v-model="examData[pc.post].mastery">
              <el-radio value="完全了解">完全了解</el-radio><el-radio value="基本了解">基本了解</el-radio><el-radio value="不了解">不了解</el-radio>
            </el-radio-group>
          </el-form-item>
        </div>

        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="考核意见（授权）">
              <el-select v-model="form.conclusion" style="width:100%" placeholder="请选择"><el-option label="同意上岗" value="同意上岗" /><el-option label="不同意上岗" value="不同意上岗" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="7"><el-form-item label="授权日期"><el-input v-model="form.auth_date" /></el-form-item></el-col>
          <el-col :span="7"><el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qrVisible" title="理论考核 · 扫码答题（扫码后填姓名）" width="380px" align-center>
      <div style="text-align:center;">
        <div style="color:#666;font-size:12px;margin-bottom:8px;">手机扫码后在浏览器作答，提交后自动判分并回写成绩</div>
        <img v-if="qrUrl" :src="qrUrl" style="width:220px;height:220px;" />
        <div style="margin-top:8px;font-size:12px;color:#888;word-break:break-all;">{{ examLink }}</div>
        <el-button size="small" style="margin-top:8px;" @click="copyLink">复制链接</el-button>
      </div>
    </el-dialog>

    <el-dialog v-model="authsVisible" :title="'自动生成的授权 · ' + (authRow ? authRow.name : '')" width="760px">
      <el-table :data="authsList" border size="small" v-loading="authsLoading">
        <el-table-column prop="instrument" label="仪器" min-width="180" />
        <el-table-column prop="post" label="岗位" min-width="140" />
        <el-table-column prop="auth_scope" label="权限" width="70" />
        <el-table-column prop="status" label="状态" width="80" />
        <el-table-column prop="valid_from" label="生效" width="100" />
        <el-table-column prop="project" label="考核项目" min-width="160" show-overflow-tooltip />
      </el-table>
      <div style="color:#999;font-size:12px;margin-top:8px;">可在「授权表」页签中管理（状态机：有条件→有效/暂停/撤销）</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import { printHtml } from '../../../utils/printHtml'
import QRCode from 'qrcode'
import { GL070_POSITIONS as META, AUTH_SCOPES } from './gl070Meta'
import { listPreJobAuth, createPreJobAuth, updatePreJobAuth, deletePreJobAuth, generatePreJobAuths, listAuthSheet, listExamBank, listPostInstrumentMap } from '../../../api/education'
import { listInstruments, getInstrumentTestItems } from '../../../api/instruments'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'name', label: '申请人', width: 110 },
  { prop: 'apply_date', label: '申请日期', width: 110 },
  { prop: 'positions', label: '考核岗位', minWidth: 180, formatter: (r) => (r.positions_json || []).join('、') },
  { prop: 'instrumentCount', label: '仪器数', width: 80, formatter: (r) => (r.instruments_json || []).length },
  { prop: 'conclusion', label: '考核意见', width: 110 },
]

const visible = ref(false)
const positions = ref([])
const instrumentCodes = ref([])
const permissions = ref([])
const banks = ref({})
const examData = ref({})
// 预初始化全部岗位的填写区——避免选岗位瞬间模板读取 undefined 导致弹窗空白
META.forEach((p) => { ensureExam(p.name) })
const form = ref(blank())
function blank() {
  return {
    id: null, name: '', apply_date: '', positions_json: [], instruments_json: [], permissions_json: [], items_json: [], exam_json: {},
    theory_eval: '', operation_eval: '', group_leader_opinion: '', director_opinion: '', conclusion: '', auth_date: '', status: '进行中', remark: '',
  }
}

// 岗位↔仪器 匹配（可视化维护；接口为空时回退到内置 gl070Meta）
const postMap = ref([])
async function loadPostMap() {
  try { const r = await listPostInstrumentMap({ page: 1, page_size: 300 }); postMap.value = (r.items || []) } catch (e) { postMap.value = [] }
}
loadPostMap()
const POSITIONS = computed(() => {
  if (!postMap.value.length) return META
  const map = new Map()
  postMap.value.forEach((x) => {
    if (!map.has(x.post)) map.set(x.post, { name: x.post, methods: x.methods_json || [], users: [], instruments: [] })
    map.get(x.post).instruments.push({ name: x.instrument_name, code: x.instrument_code, manager: x.manager })
  })
  return [...map.values()]
})

// 确保某岗位的考核填写区存在并补默认值（老记录快照缺键时自动补）
function ensureExam(post) {
  if (!examData.value[post]) examData.value[post] = {}
  const d = examData.value[post]
  d.qaNotes = d.qaNotes || {}
  d.practicalScores = d.practicalScores || {}
  d.theoryAnswers = d.theoryAnswers || {}
  if (d.qaResult === undefined) d.qaResult = '合格'
  if (d.mastery === undefined) d.mastery = '基本了解'
  if (d.trainTime === undefined) d.trainTime = ''
  if (d.trainPerson === undefined) d.trainPerson = ''
  if (!d.trainContent) d.trainContent = '岗位职责、项目SOP、仪器SOP'
  return d
}

async function loadBanks() {
  try {
    const res = await listExamBank({ page_size: 50 })
    banks.value = Object.fromEntries((res.items || []).map((b) => [b.post, b]))
  } catch (e) { banks.value = {} }
}
loadBanks()

// 仪器库（dept_no → id，用于带出关联项目）
const instByCode = ref({})
onMounted(async () => {
  try {
    const r = await listInstruments({ page: 1, page_size: 1000 })
    instByCode.value = Object.fromEntries((r.items || []).map((x) => [x.dept_no, x]))
  } catch (e) {}
})

const instrumentOptions = computed(() => {
  const sel = positions.value
  const pool = (sel && sel.length ? POSITIONS.value.filter((p) => sel.includes(p.name)) : POSITIONS.value)
  const out = []
  const seen = new Set()
  pool.forEach((p) => p.instruments.forEach((i) => {
    if (!seen.has(i.code)) { seen.add(i.code); out.push(i) }
  }))
  return out
})

// 选岗位 → 仪器自动全部带出（同步执行，消除渲染窗口期）
watch(positions, () => {
  instrumentCodes.value = instrumentOptions.value.map((i) => i.code)
positions.value.forEach((p) => { ensureExam(p) })
}, { flush: 'sync' })

// 编号 → 岗位（打印时用；老记录 instruments_json 可能没存 position）
const codeToPost = computed(() => {
  const m = {}
  POSITIONS.value.forEach((pp) => (pp.instruments || []).forEach((i) => { if (i.code) m[i.code] = pp.name }))
  return m
})
const GL070_META_ALL = computed(() => POSITIONS.value.flatMap((p) => p.instruments.map((i) => ({ ...i, position: p.name }))))

// 仪器变化 → 同步逐项行
watch(instrumentCodes, () => {
  const map = new Map(GL070_META_ALL.value.map((i) => [i.code, i]))
  form.value.items_json = instrumentCodes.value.map((c) => {
    const old = (form.value.items_json || []).find((r) => r.code === c)
    const inst = map.get(c) || {}
    return { instrument: inst.name || '', code: c, items: old ? old.items : '', result: old ? old.result : '合格' }
  })
}, { flush: 'sync' })

// 仪器关联项目（自动从关联库带出，只读展示）
// 关联项目缓存：同一台仪器只请求一次（避免每点一次就刷一次）
const projCache = new Map()
const projLoading = ref(false)
const instrumentProjects = ref([])
watch(instrumentCodes, async () => {
  projLoading.value = true
  const rows = []
  for (const c of instrumentCodes.value) {
    const inst = GL070_META_ALL.value.find((i) => i.code === c) || {}
    let projects = projCache.get(c)
    if (projects === undefined) {
      projects = ''
      const dbInst = instByCode.value[c]
      if (dbInst) {
        try {
          const items = await getInstrumentTestItems(dbInst.id)
          projects = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
        } catch (e) { projects = '' }
      }
      projCache.set(c, projects)
    }
    rows.push({ code: c, name: inst.name || '', projects })
  }
  instrumentProjects.value = rows
  // 把自动带出的项目写入记录（保存后打印才有项目）
  rows.forEach((r) => {
    const it = (form.value.items_json || []).find((x) => x.code === r.code)
    if (it && r.projects) it.items = r.projects
  })
  projLoading.value = false
})

// ===== 按岗位考核区 =====
const examAreas = computed(() => positions.value.map((post) => {
  const bank = banks.value[post] || { post, methods_json: ['实操考核'], qa_json: [], practical_json: [], theory_json: {} }
  const methods = bank.methods_json && bank.methods_json.length ? bank.methods_json : ['实操考核']
  const practicalTotal = (bank.practical_json || []).reduce((s, p) => s + (p.score || 0), 0)
  const theoryFull = ((bank.theory_json && (bank.theory_json.single || []).length) || 0) * 2
    + ((bank.theory_json && (bank.theory_json.multi || []).length) || 0) * 4
    + ((bank.theory_json && (bank.theory_json.judge || []).length) || 0) * 2
  return { post, bank, methods, practicalTotal, theoryFull }
}))
function practicalScore(pc) {
  return (pc.bank.practical_json || []).reduce((s, p, i) => s + (Number((examData.value[pc.post] || {}).practicalScores?.[i]) || 0), 0)
}
// 注意：pc.theoryFull 是数值属性，模板/判分里用函数取值（曾误写 theoryFull(pc) 导致渲染崩溃、弹窗空白）
function theoryFull(pc) { return pc.theoryFull || 0 }
// 百分制（每岗位满分 100）
function theoryPct(pc) { const t = theoryFull(pc); return t ? Math.round(theoryScore(pc) * 100 / t) : 0 }
function practicalPct(pc) { const t = pc.practicalTotal || 0; return t ? Math.round(practicalScore(pc) * 100 / t) : 0 }
// 答案容错：题库里多选答案可能存成数组（历史数据），统一转字符串比较
function ansStr(a) { return Array.isArray(a) ? a.join('') : String(a == null ? '' : a) }
function theoryScore(pc) {
  let s = 0
  const d = examData.value[pc.post] || {}
  const T = pc.bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (ansStr(d.theoryAnswers?.['s' + i]) === ansStr(t.answer).slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => {
    const got = (d.theoryAnswers?.['m' + i] || []).slice().sort().join('')
    if (got && got === t.answer.split('').sort().join('')) s += 4
  })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === t.answer) s += 2 })
  return s
}
function postPass(pc) {
  if (pc.methods.includes('实操考核') && (pc.practicalTotal || 0) > 0 && practicalPct(pc) < 80) return false
  if (pc.methods.includes('理论考核') && theoryFull(pc) > 0 && theoryPct(pc) < 60) return false
  if (pc.methods.includes('口头问答') && (examData.value[pc.post] || {}).qaResult === '不合格') return false
  return true
}
function autoJudge() {
  const allPass = examAreas.value.every(postPass)
  form.value.conclusion = allPass ? '同意上岗' : '不同意上岗'
  form.value.exam_json = JSON.parse(JSON.stringify(examData.value))
  ElMessage.success(allPass ? '全部岗位考核合格 → 考核意见「同意上岗」，可点「生成授权」' : '存在未达合格线岗位 → 考核意见「不同意上岗」')
}

function openForm(row) {
  if (row) {
    form.value = { ...blank(), ...row }
    positions.value = [...(row.positions_json || [])]
    instrumentCodes.value = (row.instruments_json || []).map((i) => i.code)
    permissions.value = [...(row.permissions_json || [])]
    examData.value = JSON.parse(JSON.stringify(row.exam_json || {}))
positions.value.forEach((p) => { ensureExam(p) })
  } else {
    form.value = blank(); positions.value = []; instrumentCodes.value = []; permissions.value = []
    examData.value = JSON.parse(JSON.stringify(examData.value))
  }
  visible.value = true
  // 打开即预热该记录的关联项目，并写入 items_json（保存后固化，打印不再依赖缓存）
  warmProjects([form.value]).then(() => {
    ;(form.value.instruments_json || []).forEach((i) => {
      const it = (form.value.items_json || []).find((x) => x.code === i.code)
      const pj = projCache.get(i.code)
      if (it && pj && !it.items) it.items = pj
    })
  })
}
async function save() {
  try {
    form.value.exam_json = JSON.parse(JSON.stringify(examData.value))
    const payload = {
      ...form.value,
      positions_json: positions.value,
      instruments_json: instrumentOptions.value.filter((i) => instrumentCodes.value.includes(i.code)),
      permissions_json: permissions.value,
    }
    if (payload.id) await updatePreJobAuth(payload.id, payload)
    else await createPreJobAuth(payload)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deletePreJobAuth(row.id); ElMessage.success('已删除'); tableRef.value?.refresh() } catch (e) {}
}
// 列表加载后，后台预热各行仪器的关联项目（打印是同步的，必须提前缓存）
async function warmProjects(rows) {
  // 仪器库未就绪时先加载（否则按编号查不到仪器 → 项目永远为空）
  if (!Object.keys(instByCode.value).length) {
    try {
      const r = await listInstruments({ page: 1, page_size: 1000 })
      instByCode.value = Object.fromEntries((r.items || []).map((x) => [x.dept_no, x]))
    } catch (e) { /* ignore */ }
  }
  const codes = []
  ;(rows || []).forEach((r) => (r.instruments_json || []).forEach((i) => { if (i.code) codes.push(i.code) }))
  const todo = [...new Set(codes)].filter((c) => !projCache.has(c))
  const one = async (c) => {
    const db = instByCode.value[c]
    if (!db) return   // 查不到仪器不写缓存，留给下次重试
    let pj = ''
    try {
      const items = await getInstrumentTestItems(db.id)
      pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim()).join('、')
    } catch (e) { pj = '' }
    projCache.set(c, pj)
  }
  // 并发分批（每批 6 个）加速预热
  for (let i = 0; i < todo.length; i += 6) {
    await Promise.all(todo.slice(i, i + 6).map(one))
  }
}
async function fetch(params) {
  const res = await listPreJobAuth(params)
  warmProjects(res.items || [])
  return res
}

// ===== P3：同意上岗 → 自动生成授权 =====
async function genAuths(row) {
  const n = (row.instruments_json || []).length
  const s = (row.permissions_json || []).length
  try {
    await ElMessageBox.confirm(
      `将为 ${row.name} 按考核的 ${n} 台仪器 × ${s} 级权限生成授权记录（初始状态「有条件」= 监督期内），可在「授权表」页签管理。确认生成？`,
      '生成授权确认', { type: 'warning', confirmButtonText: '生成' }
    )
  } catch (e) { return }
  try {
    const res = await generatePreJobAuths(row.id)
    ElMessage.success(`已生成 ${res.created} 条授权，批次 ${res.batch_id}`)
    tableRef.value?.refresh()
  } catch (e) { ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message)) }
}
const authsVisible = ref(false)
const authsLoading = ref(false)
const authsList = ref([])
const authRow = ref(null)
async function viewAuths(row) {
  authRow.value = row; authsVisible.value = true; authsLoading.value = true
  try {
    const res = await listAuthSheet({ q: `岗前培训授权-单${row.id}`, page_size: 100 })
    authsList.value = (res.items || []).filter((a) => a.source_assessment_id === row.id)
  } finally { authsLoading.value = false }
}

// ===== 扫码答题 =====
const qrVisible = ref(false)
const qrUrl = ref('')
const examLink = ref('')
// 通用二维码：任何人扫 → 填姓名 → 找到自己的考核单 → 作答
async function showQrPublic() {
  examLink.value = window.location.origin + '/exam'
  try { qrUrl.value = await QRCode.toDataURL(examLink.value, { width: 440 }) } catch (e) { qrUrl.value = '' }
  qrVisible.value = true
}
async function showQr(row) {
  examLink.value = window.location.origin + '/exam/' + row.id
  try { qrUrl.value = await QRCode.toDataURL(examLink.value, { width: 440 }) } catch (e) { qrUrl.value = '' }
  qrVisible.value = true
}
function copyLink() {
  try { navigator.clipboard.writeText(examLink.value); ElMessage.success('链接已复制') } catch (e) { ElMessage.info(examLink.value) }
}

// 盛京版式打印
function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }
// 同步打印：必须用已缓存的题库（await 之后再 window.open 会被浏览器当弹窗拦截）
async function printForm(row) {
  const bankMap = banks.value || {}
  if (!Object.keys(bankMap).length) loadBanks()
  const missing = (row.instruments_json || []).some((i) => i.code && !projCache.has(i.code))
  await warmProjects([row])

  const posts = row.positions_json || []
  const allInsts = row.instruments_json || []
  const instsOfPost = (post) => allInsts.filter((i) => (i.position || codeToPost.value[i.code] || '') === post)
  const projOf = (code) => {
    const r = (row.items_json || []).find((x) => x.code === code)
    const fromRow = r ? (r.items || '') : ''
    return fromRow || projCache.get(code) || ''
  }
  const projOfPost = (post) => [...new Set(instsOfPost(post).map((i) => projOf(i.code)).filter(Boolean))].join('；')
  const boxRow = (label, value, fs) => `<tr><td style="width:80px;text-align:center;background:#f7f7f7;border:1px solid #333;padding:5px;">${label}</td><td style="border:1px solid #333;padding:5px;font-size:${fs || 12}px;">${value || ''}</td></tr>`
  const pageBreak = '<div style="page-break-after: always;"></div>'

  const instNamesAll = [...new Set(allInsts.map((i) => i.name).filter(Boolean))].join('、')
  const allProjText = [...new Set(allInsts.map((i) => projOf(i.code)).filter(Boolean))].join('；')

  // ===== 第一页 =====
  const page1 = `
    <h2 style="text-align:center;letter-spacing:3px;margin:0 0 4px;">岗前培训考核及授权表</h2>
    <table style="border:1.5px solid #333;font-size:13px;">
      <tr><td style="width:90px;text-align:center;background:#f7f7f7;">申请人</td><td style="width:180px;text-align:center;">${esc(row.name)}</td><td style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td><td style="text-align:center;">${esc(row.apply_date)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3" style="padding:4px 8px;">${esc(posts.join('、'))}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">仪器</td><td colspan="3" style="padding:4px 8px;font-size:11px;line-height:1.3;">${esc(instNamesAll)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">项目</td><td colspan="3" style="padding:4px 8px;font-size:9px;line-height:1.25;">${esc(allProjText)}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">授权权限</td><td colspan="3" style="padding:4px 8px;">${esc((row.permissions_json || []).join('、'))}</td></tr>
    </table>
    <h3>考核意见</h3>
    <table style="border:1.5px solid #333;font-size:13px;">
      <tr><td style="width:130px;text-align:center;background:#f7f7f7;">考核意见（授权）</td><td style="padding:6px 10px;">${esc(row.conclusion)}${row.auth_date ? '　授权日期：' + esc(row.auth_date) : ''}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">备注</td><td style="padding:6px 10px;min-height:36px;">${esc(row.remark)}</td></tr>
    </table>
    <div style="margin-top:34px;text-align:center;font-size:14px;letter-spacing:1px;">
      员工签字：　　　　　　　　组长签字：　　　　　　　　日期：
    </div>
    <div style="margin-top:30px;padding-top:6px;border-top:1px solid #999;font-size:11px;color:#333;text-align:center;">
      表格编号：BG-SM-PX-002　　　　民航总医院检验科生化免疫组　　　　失效日期：2026.9.15
    </div>
    ${pageBreak}`

  // ===== 每岗位一页 =====
  const pages = posts.map((post) => {
    const bank = bankMap[post] || {}
    const methods = bank.methods_json && bank.methods_json.length ? bank.methods_json : ['实操考核']
    const d = (row.exam_json || {})[post] || {}
    const pTotal = (bank.practical_json || []).reduce((x, y) => x + (y.score || 0), 0)
    const tFull = ((bank.theory_json && (bank.theory_json.single || []).length) || 0) * 2
      + ((bank.theory_json && (bank.theory_json.multi || []).length) || 0) * 4
      + ((bank.theory_json && (bank.theory_json.judge || []).length) || 0) * 2
    const pGot = (bank.practical_json || []).reduce((x, y, i) => x + (Number((d.practicalScores || {})[i]) || 0), 0)
    const pPct = pTotal ? Math.round(pGot * 100 / pTotal) : 0
    const tPct = tFull ? Math.round(theoryScoreOf2(row, post, bank) * 100 / tFull) : 0

    // 口头问答：问题清单
    const qaList = `<div style="font-size:10px;line-height:1.35;">${(bank.qa_json || []).map((q, i) => `<div>${i + 1}. ${esc(q.q)}</div>`).join('')}</div>`
    // 实操：要点 + 分值 + 得分
    const prRows = (bank.practical_json || []).map((x, i) => `<tr><td style="border:1px solid #333;padding:3px 4px;font-size:10px;line-height:1.3;">${i + 1}. ${esc(x.point)}</td><td style="border:1px solid #333;padding:4px;width:60px;text-align:center;">${x.score}</td><td style="border:1px solid #333;padding:4px;width:60px;text-align:center;">${(d.practicalScores || {})[i] || ''}</td></tr>`).join('')
    // 理论：题目 + 选项 + 本人作答 + 对错判定
    const ansMap = d.theoryAnswers || {}
    const th = []
    const answerLine = (picked, right, multi) => {
      const pStr = Array.isArray(picked) ? picked.join('') : String(picked == null ? '' : picked)
      const rStr = ansStr(right)
      let ok = false
      if (pStr) ok = multi ? (pStr.split('').sort().join('') === rStr.split('').sort().join('')) : (pStr === rStr)
      const mark = pStr ? (ok ? '<b>✓ 正确</b>' : `<b>✗ 错误</b>（正确答案：${esc(rStr)}）`) : '（未作答）'
      return `<div style="font-size:10px;color:#333;">被考核人选择：<b>${esc(pStr || '—')}</b>　${mark}</div>`
    }
    ;((bank.theory_json || {}).single || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;font-size:10px;line-height:1.35;">${i + 1}. ${esc(t.q)}<br>${(t.options || []).map((o) => esc(o)).join('　　')}<br>${answerLine(ansMap['s' + i], t.answer, false)}</div>`))
    ;((bank.theory_json || {}).multi || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;font-size:10px;line-height:1.35;">${i + 1}. ${esc(t.q)}<br>${(t.options || []).map((o) => esc(o)).join('　　')}<br>${answerLine(ansMap['m' + i], t.answer, true)}</div>`))
    ;((bank.theory_json || {}).judge || []).forEach((t, i) => th.push(`<div style="margin-bottom:4px;font-size:10px;line-height:1.35;">${i + 1}. ${esc(t.q)}　（对 / 错）<br>${answerLine(ansMap['j' + i], t.answer, false)}</div>`))

    return `
    <h3 style="margin:0 0 6px;">岗位：${esc(post)}</h3>
    <table style="border:1.5px solid #333;font-size:12px;">
      <tr><td style="width:80px;text-align:center;background:#f7f7f7;">培训时间</td><td style="text-align:center;">${esc(d.trainTime || '')}</td><td style="width:70px;text-align:center;background:#f7f7f7;">培训人</td><td style="text-align:center;">${esc(d.trainPerson || '')}</td></tr>
      <tr><td style="text-align:center;background:#f7f7f7;">培训内容</td><td colspan="3" style="padding:4px 8px;">${esc(d.trainContent || '')}</td></tr>
    </table>
    <table style="border-collapse:collapse;width:100%;font-size:12px;">
      ${boxRow('仪器', esc(instsOfPost(post).map((i) => i.name).join('、')))}
      ${boxRow('项目', esc(projOfPost(post)), 9)}
    </table>
    ${methods.includes('口头问答') ? `<h4 style="margin:8px 0 3px;font-size:12px;">一、口头问答（考核结果：${esc(d.qaResult || '')}）</h4>${qaList}` : ''}
    ${prRows ? `<h4 style="margin:8px 0 3px;font-size:12px;">二、实操考核（${pPct} / 100 分，合格线 80）</h4>
      <table style="border-collapse:collapse;width:100%;font-size:12px;">
        <tr><th style="border:1px solid #333;background:#f1f5f9;padding:3px 4px;font-size:10px;">考核要点</th><th style="border:1px solid #333;background:#f1f5f9;padding:3px 4px;font-size:10px;width:50px;">分值</th><th style="border:1px solid #333;background:#f1f5f9;padding:3px 4px;font-size:10px;width:50px;">得分</th></tr>
        ${prRows}</table>` : ''}
    ${th.length ? `<h4 style="margin:8px 0 3px;font-size:12px;">三、理论考核（${tPct} / 100 分，合格线 60）</h4>${th.join('')}` : ''}
    <table style="border-collapse:collapse;width:100%;font-size:12px;margin-top:8px;">
      ${boxRow('考核方式', esc(methods.join('、')))}
      ${boxRow('掌握程度', esc(d.mastery || ''))}
    </table>
    ${pageBreak}`
  }).join('')

  printHtml('岗前培训考核及授权表', page1 + pages)
}
// 某岗位理论得分（按 job 快照判分）
function theoryScoreOf2(row, post, bank) {
  let s = 0
  const d = (row.exam_json || {})[post] || {}
  const T = bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (ansStr(d.theoryAnswers?.['s' + i]) === ansStr(t.answer).slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => { const g = (d.theoryAnswers?.['m' + i] || []).slice().sort().join(''); if (g && g === ansStr(t.answer).split('').sort().join('')) s += 4 })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === ansStr(t.answer)) s += 2 })
  return s
}
function practicalPctOf(row, pp) { const t = pp.practicalTotal || 0; return t ? Math.round(practicalScoreOf(row, pp) * 100 / t) : 0 }
function theoryPctOf(row, pp) { const t = pp.theoryFull || 0; return t ? Math.round(theoryScoreOf(row, pp) * 100 / t) : 0 }
function theoryScoreOf(row, pp) {
  let s = 0
  const d = (row.exam_json || {})[pp.post] || {}
  const T = pp.bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (ansStr(d.theoryAnswers?.['s' + i]) === ansStr(t.answer).slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => { const g = (d.theoryAnswers?.['m' + i] || []).slice().sort().join(''); if (g && g === ansStr(t.answer).split('').sort().join('')) s += 4 })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === ansStr(t.answer)) s += 2 })
  return s
}
</script>
