<template>
  <div class="pre-job-auth">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索申请人"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button v-if="row.conclusion === '通过' && !row.batch_id" link type="warning" @click="genAuths(row)">生成授权</el-button>
        <el-button v-if="row.batch_id" link type="success" @click="viewAuths(row)">查看授权</el-button>
        <el-button link type="primary" @click="printForm(row)">打印</el-button>
      </template>
    </CrudTable>

    <el-dialog v-model="visible" :title="form.id ? '编辑岗前培训考核及授权表' : '新增岗前培训考核及授权表'" width="860px" top="3vh">
      <el-form :model="form" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="申请人"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="申请日期"><el-input v-model="form.apply_date" placeholder="如 2026-09-08" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="考核岗位（多选）">
          <el-select v-model="positions" multiple style="width:100%" placeholder="按 GL-070 选择岗位，仪器自动带出">
            <el-option v-for="p in META" :key="p.name" :label="p.name" :value="p.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="考核仪器（自动带出，可调整）">
          <el-select v-model="instrumentCodes" multiple style="width:100%">
            <el-option v-for="i in instrumentOptions" :key="i.code" :label="i.name + '（' + i.code.replace('MHZYY-JYK-', '') + '）'" :value="i.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权权限（多选）">
          <el-select v-model="permissions" multiple style="width:100%" placeholder="操作 / 复核 / 报告">
            <el-option v-for="s in AUTH_SCOPES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">逐项去仪器/项目考核</el-divider>
        <el-table :data="form.items_json" border size="small">
          <el-table-column label="仪器" min-width="200">
            <template #default="{ row }">{{ row.instrument }}（{{ row.code.replace('MHZYY-JYK-', '') }}）</template>
          </el-table-column>
          <el-table-column label="考核项目" min-width="220">
            <template #default="{ row }"><el-input v-model="row.items" size="small" placeholder="考核的检验项目/内容" /></template>
          </el-table-column>
          <el-table-column label="结果" width="110">
            <template #default="{ row }">
              <el-select v-model="row.result" size="small"><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select>
            </template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">按岗位考核（方式与题库自动带出，可填写）</el-divider>
        <el-button size="small" @click="autoJudge()" type="warning" style="margin-bottom:8px;">按考核结果自动判定结论</el-button>
        <div v-for="pc in examAreas" :key="pc.post" style="border:1px solid #e4e7ed;border-radius:6px;padding:10px 12px;margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <b style="font-size:15px;">{{ pc.post }}</b>
            <el-tag size="small" type="info">{{ pc.methods.join(' / ') }}</el-tag>
            <el-tag size="small" :type="pc.pass ? 'success' : 'warning'">{{ pc.pass ? '合格' : '未达合格线' }}</el-tag>
          </div>
            <template v-if="pc.methods.includes('口头问答')">
              <div style="font-weight:600;margin:4px 0;">口头问答（逐题记录要点）</div>
              <div v-for="(qa, qi) in pc.bank.qa_json || []" :key="'q' + qi" style="margin-bottom:6px;">
                <div>{{ qi + 1 }}. {{ qa.q }}</div>
                <el-input v-model="examData[pc.post].qaNotes[qi]" size="small" type="textarea" :rows="1" placeholder="作答要点/评价（参考答案见题库）" />
              </div>
            </template>
            <template v-if="pc.methods.includes('实操考核')">
              <div style="font-weight:600;margin:4px 0;">实操考核（要点打分，满分 {{ pc.practicalTotal }}）</div>
              <div v-for="(pt, pi) in pc.bank.practical_json || []" :key="'p' + pi" style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <span style="flex:1;">{{ pi + 1 }}. {{ pt.point }}</span>
                <span style="color:#888;">满分 {{ pt.score }}</span>
                <el-input-number v-model="examData[pc.post].practicalScores[pi]" size="small" :min="0" :max="pt.score" style="width:110px;" />
              </div>
              <div>实操得分：<b>{{ practicalScore(pc) }}</b> / {{ pc.practicalTotal }}　合格线 {{ Math.ceil(pc.practicalTotal * 0.8) }}</div>
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
              <div>理论得分：<b>{{ theoryScore(pc) }}</b> / {{ theoryFull(pc) }}　合格线 {{ Math.ceil(theoryFull(pc) * 0.6) }}</div>
            </template>
        </div>

        <el-form-item label="理论考核" style="margin-top:12px"><el-input v-model="form.theory_eval" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="操作考核"><el-input v-model="form.operation_eval" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="组长意见"><el-input v-model="form.group_leader_opinion" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="主任意见"><el-input v-model="form.director_opinion" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="结论">
              <el-select v-model="form.conclusion" style="width:100%"><el-option label="待审核" value="待审核" /><el-option label="通过" value="通过" /><el-option label="不通过" value="不通过" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="授权日期"><el-input v-model="form.auth_date" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
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
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import { printHtml } from '../../../utils/printHtml'
import { GL070_POSITIONS as META, AUTH_SCOPES } from './gl070Meta'
import { listPreJobAuth, createPreJobAuth, updatePreJobAuth, deletePreJobAuth, generatePreJobAuths, listAuthSheet, listExamBank } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'name', label: '申请人', width: 110 },
  { prop: 'apply_date', label: '申请日期', width: 110 },
  { prop: 'positions', label: '考核岗位', minWidth: 180, formatter: (r) => (r.positions_json || []).join('、') },
  { prop: 'instrumentCount', label: '仪器数', width: 80, formatter: (r) => (r.instruments_json || []).length },
  { prop: 'conclusion', label: '结论', width: 90 },
]

const visible = ref(false)
const positions = ref([])
const instrumentCodes = ref([])
const permissions = ref([])
const banks = ref({})

const examData = ref({})
const form = ref(blank())
function blank() {
  return {
    id: null, name: '', apply_date: '', positions_json: [], instruments_json: [], permissions_json: [], items_json: [], exam_json: {},
    theory_eval: '', operation_eval: '', group_leader_opinion: '', director_opinion: '', conclusion: '待审核', auth_date: '', status: '进行中', remark: '',
  }
}

// 题库（按岗位）
async function loadBanks() {
  try {
    const res = await listExamBank({ page_size: 50 })
    banks.value = Object.fromEntries((res.items || []).map((b) => [b.post, b]))
  } catch (e) { banks.value = {} }
}
loadBanks()

// 选岗位 → 仪器自动全部带出；并初始化该岗位的考核填写区
watch(positions, () => {
  instrumentCodes.value = instrumentOptions.value.map((i) => i.code)
  const missing = positions.value.filter((p) => !examData.value[p])
  missing.forEach((p) => { examData.value[p] = { qaNotes: {}, practicalScores: {}, theoryAnswers: {} } })

})

const instrumentOptions = computed(() => {
  const sel = positions.value
  const pool = (sel && sel.length ? META.filter((p) => sel.includes(p.name)) : META)
  const out = []
  const seen = new Set()
  pool.forEach((p) => p.instruments.forEach((i) => {
    if (!seen.has(i.code)) { seen.add(i.code); out.push(i) }
  }))
  return out
})

// 仪器变化 → 同步逐项考核行
watch(instrumentCodes, () => {
  const map = new Map(GL070_META_ALL.value.map((i) => [i.code, i]))
  form.value.items_json = instrumentCodes.value.map((c) => {
    const old = (form.value.items_json || []).find((r) => r.code === c)
    const inst = map.get(c) || {}
    return { instrument: inst.name || '', code: c, items: old ? old.items : '', result: old ? old.result : '合格' }
  })
})
const GL070_META_ALL = computed(() => META.flatMap((p) => p.instruments.map((i) => ({ ...i, position: p.name }))))

// ===== 按岗位考核区：方式/题库自动带出，作答打分自动汇总 =====
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
  const got = (pc.bank.practical_json || []).reduce((s, p, i) => s + (Number((examData.value[pc.post] || {}).practicalScores?.[i]) || 0), 0)
  return got
}
function theoryScore(pc) {
  let s = 0
  const d = examData.value[pc.post] || {}
  const T = pc.bank.theory_json || {}
  ;(T.single || []).forEach((t, i) => { if (d.theoryAnswers?.['s' + i] === t.answer.slice(0, 1)) s += 2 })
  ;(T.multi || []).forEach((t, i) => {
    const got = (d.theoryAnswers?.['m' + i] || []).slice().sort().join('')
    if (got && got === t.answer.split('').sort().join('')) s += 4
  })
  ;(T.judge || []).forEach((t, i) => { if (d.theoryAnswers?.['j' + i] === t.answer) s += 2 })
  return s
}
function postPass(pc) {
  if (pc.methods.includes('实操考核') && practicalScore(pc) < Math.ceil(pc.practicalTotal * 0.8)) return false
  if (pc.methods.includes('理论考核') && theoryScore(pc) < Math.ceil(theoryFull(pc) * 0.6)) return false
  return true
}
function autoJudge() {
  const allPass = examAreas.value.every(postPass)
  form.value.conclusion = allPass ? '通过' : '不通过'
  form.value.exam_json = JSON.parse(JSON.stringify(examData.value))
  ElMessage.success(allPass ? '全部岗位考核合格 → 结论「通过」，可点「生成授权」' : '存在未达合格线岗位 → 结论「不通过」')
}

function openForm(row) {
  if (row) {
    form.value = { ...blank(), ...row }
    positions.value = [...(row.positions_json || [])]
    instrumentCodes.value = (row.instruments_json || []).map((i) => i.code)
    permissions.value = [...(row.permissions_json || [])]
    examData.value = JSON.parse(JSON.stringify(row.exam_json || {}))
    positions.value.forEach((p) => { if (!examData.value[p]) examData.value[p] = { qaNotes: {}, practicalScores: {}, theoryAnswers: {} } })
  } else {
    form.value = blank(); positions.value = []; instrumentCodes.value = []; permissions.value = []; examData.value = {}
  }
  visible.value = true
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
function fetch(params) { return listPreJobAuth(params) }

// ===== P3：同意上岗 → 自动生成授权（batch_id 分组） =====
async function genAuths(row) {
  const n = (row.instruments_json || []).length
  try {
    await ElMessageBox.confirm(
      `将为 ${row.name} 按考核通过的 ${n} 台仪器逐台生成授权记录（初始状态「有条件」= 监督期内），可在「授权表」页签管理。确认生成？`,
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

// 盛京版式打印
function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }
function printForm(row) {
  const inst = (row.instruments_json || []).map((i) => `<tr><td style="text-align:center;">${esc(i.position || '')}</td><td>${esc(i.name)}</td><td style="text-align:center;">${esc(i.code)}</td><td></td><td></td></tr>`).join('')
  const perm = (row.permissions_json || []).join('、')
  const html = `
  <h2 style="text-align:center;font-size:20px;letter-spacing:3px;margin:0 0 6px;">岗前培训考核及授权表</h2>
  <div style="text-align:center;color:#555;font-size:12px;margin-bottom:10px;">表格编号：BG-SM-PX-002　　检验科生化免疫组</div>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td class="lbl" style="width:90px;text-align:center;background:#f7f7f7;">申请人</td><td style="width:180px;text-align:center;height:30px;">${esc(row.name)}</td><td class="lbl" style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td><td style="text-align:center;">${esc(row.apply_date)}</td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3" style="padding:6px 10px;">${esc((row.positions_json || []).join('、'))}</td></tr>
  </table>
  <h3>一、考核仪器及项目（逐项）</h3>
  <table style="border-collapse:collapse;width:100%;font-size:12px;">
    <tr><th style="border:1px solid #333;background:#f1f5f9;padding:5px;">岗位</th><th style="border:1px solid #333;background:#f1f5f9;padding:5px;">仪器</th><th style="border:1px solid #333;background:#f1f5f9;padding:5px;">仪器编号</th><th style="border:1px solid #333;background:#f1f5f9;padding:5px;width:26%;">考核项目</th><th style="border:1px solid #333;background:#f1f5f9;padding:5px;width:10%;">结果</th></tr>
    ${inst}
  </table>
  <h3>二、考核情况</h3>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td class="lbl" style="width:90px;text-align:center;background:#f7f7f7;">理论考核</td><td style="padding:6px 10px;min-height:40px;">${esc(row.theory_eval)}</td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">操作考核</td><td style="padding:6px 10px;">${esc(row.operation_eval)}</td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">授权岗位</td><td style="padding:6px 10px;">${esc(perm)}</td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">组长意见</td><td style="padding:6px 10px;height:70px;vertical-align:top;">${esc(row.group_leader_opinion)}<div style="margin-top:14px;text-align:right;">组长签字：　　　　　　日期：　　　　</div></td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">主任意见</td><td style="padding:6px 10px;height:70px;vertical-align:top;">${esc(row.director_opinion)}<div style="margin-top:14px;text-align:right;">科主任签字：　　　　　　日期：　　　　</div></td></tr>
    <tr><td class="lbl" style="text-align:center;background:#f7f7f7;">结论</td><td style="padding:6px 10px;">${esc(row.conclusion)}${row.auth_date ? '　授权日期：' + esc(row.auth_date) : ''}</td></tr>
  </table>`
  printHtml('岗前培训考核及授权表', html)
}
</script>
