<template>
  <div class="auth-sheet">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <div>
        <h2 class="title" style="margin:0;">授权表</h2>
        <span style="color:#666;font-size:12px;">一人一条：岗位、仪器、权限均为多选；项目由关联库自动带出</span>
      </div>
      <div style="display:flex;gap:8px;">
        <el-input v-model="kw" size="small" placeholder="搜索姓名/仪器" style="width:180px;" clearable />
        <el-button type="primary" size="small" :disabled="!canWrite" @click="openForm()">新增授权</el-button>
      </div>
    </div>

    <el-table :data="filtered" border size="small" v-loading="loading">
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="department" label="部门" width="110" />
      <el-table-column label="授权岗位" min-width="160">
        <template #default="{ row }">{{ postsOf(row).join('、') }}</template>
      </el-table-column>
      <el-table-column label="授权仪器" min-width="200">
        <template #default="{ row }">{{ instNames(row).join('、') || row.instrument }}</template>
      </el-table-column>
      <el-table-column label="权限" width="120">
        <template #default="{ row }">{{ scopesOf(row).join('、') || row.auth_scope }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" />
      <el-table-column prop="valid_until" label="有效期至" width="110" />
      <el-table-column prop="authorizer" label="授权人" width="90" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button link type="primary" :disabled="!canWrite" @click="openForm(row)">编辑</el-button>
          <el-button link type="primary" @click="printRow(row)">打印</el-button>
          <el-button link type="danger" :disabled="!canWrite" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑授权 · ' + form.name : '新增授权'" width="820px" top="3vh">
      <el-form :model="form" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="姓名">
              <el-select v-model="form.name" filterable allow-create default-first-option @change="onNameChange" style="width:100%">
                <el-option v-for="p in people" :key="p.id" :label="p.name" :value="p.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="部门"><el-input v-model="form.department" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%"><el-option v-for="s in STATUS" :key="s" :label="s" :value="s" /></el-select>
          </el-form-item></el-col>
        </el-row>

        <el-form-item label="授权岗位（多选）">
          <el-select v-model="posts" multiple style="width:100%" @change="onPostChange">
            <el-option v-for="p in postNames" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权仪器（多选）">
          <el-select v-model="instCodes" multiple style="width:100%">
            <el-option v-for="i in instOptions" :key="i.code" :label="i.name + '（' + i.code.replace('MHZYY-JYK-', '') + '）'" :value="i.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权权限（多选）">
          <el-select v-model="scopes" multiple style="width:100%">
            <el-option v-for="s in SCOPES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目/方法（自动全带出）">
          <div style="max-height:110px;overflow:auto;border:1px solid #eee;border-radius:4px;padding:6px;font-size:12px;color:#444;">
            {{ projText || '（选择仪器后自动列出全部关联项目）' }}
          </div>
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="授权人"><el-input v-model="form.authorizer" /></el-form-item></el-col>
          <el-col :span="10"><el-form-item label="授权人资质"><el-input v-model="form.authorizer_qualification" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="授权日期"><el-input v-model="form.auth_date" placeholder="2026-09-10" @change="calcValid" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="有效期起"><el-input v-model="form.valid_from" @change="calcValid" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="有效期至"><el-input v-model="form.valid_until" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" :title="'授权详情 · ' + (current ? current.name : '')" width="760px">
      <el-descriptions :column="2" border v-if="current">
        <el-descriptions-item label="部门">{{ current.department }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ current.status }}</el-descriptions-item>
        <el-descriptions-item label="授权岗位" :span="2">{{ postsOf(current).join('、') }}</el-descriptions-item>
        <el-descriptions-item label="授权仪器" :span="2">{{ instNames(current).join('、') || current.instrument }}</el-descriptions-item>
        <el-descriptions-item label="权限" :span="2">{{ scopesOf(current).join('、') || current.auth_scope }}</el-descriptions-item>
        <el-descriptions-item label="项目/方法（全部关联项目）" :span="2">
          <div style="max-height:180px;overflow:auto;">{{ detailProj || '加载中…' }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="授权人">{{ current.authorizer }}</el-descriptions-item>
        <el-descriptions-item label="授权人资质">{{ current.authorizer_qualification }}</el-descriptions-item>
        <el-descriptions-item label="授权日期">{{ current.auth_date }}</el-descriptions-item>
        <el-descriptions-item label="有效期">{{ current.valid_from }} ~ {{ current.valid_until }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { printHtml } from '../../../utils/printHtml'
import { GL070_POSITIONS } from './gl070Meta'
import { listAuthSheet, getAuthSheet, createAuthSheet, updateAuthSheet, deleteAuthSheet, listPersonnel, listPostInstrumentMap } from '../../../api/education'
import { listInstruments, getInstrumentTestItems } from '../../../api/instruments'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const SCOPES = ['操作', '复核', '报告']
const STATUS = ['有效', '有条件', '暂停', '撤销']

const list = ref([])
const loading = ref(false)
const kw = ref('')
const people = ref([])
const instByCode = ref({})
const postMap = ref([])
const visible = ref(false)
const detailVisible = ref(false)
const current = ref(null)
const posts = ref([])
const instCodes = ref([])
const scopes = ref([])
const projCache = new Map()
const projText = ref('')
const detailProj = ref('')
const form = ref(blank())

function blank() {
  return {
    id: null, name: '', person_id: null, department: '生化免疫组', post: '', instrument: '', auth_scope: '',
    project: '', status: '有效', valid_from: '', valid_until: '', auth_date: '',
    authorizer: '金子铮', authorizer_qualification: '免疫组组长/主治医师/本领域6年',
    posts_json: [], instruments_json: [], scopes_json: [], remark: '',
  }
}

const postNames = computed(() => (postMap.value.length ? [...new Set(postMap.value.map((x) => x.post))] : GL070_POSITIONS.map((p) => p.name)))
const instOptions = computed(() => {
  if (postMap.value.length) {
    const sel = posts.value
    const rows = sel && sel.length ? postMap.value.filter((x) => sel.includes(x.post)) : postMap.value
    const seen = new Set()
    return rows.filter((x) => (seen.has(x.instrument_code) ? false : seen.add(x.instrument_code)))
      .map((x) => ({ name: x.instrument_name, code: x.instrument_code }))
  }
  const pool = posts.value && posts.value.length ? GL070_POSITIONS.filter((p) => posts.value.includes(p.name)) : GL070_POSITIONS
  const out = []
  const seen = new Set()
  pool.forEach((p) => p.instruments.forEach((i) => { if (!seen.has(i.code)) { seen.add(i.code); out.push({ name: i.name, code: i.code }) } }))
  return out
})

const filtered = computed(() => {
  const k = kw.value.trim()
  if (!k) return list.value
  return list.value.filter((r) => (r.name || '').includes(k) || (r.instrument || '').includes(k))
})
function postsOf(r) { return r.posts_json && r.posts_json.length ? r.posts_json : String(r.post || '').split('、').filter(Boolean) }
function instNames(r) { return (r.instruments_json || []).map((i) => i.name || i).filter(Boolean) }
function scopesOf(r) { return r.scopes_json && r.scopes_json.length ? r.scopes_json : String(r.auth_scope || '').split('、').filter(Boolean) }

onMounted(async () => {
  await refresh()
  try { const p = await listPersonnel({ page: 1, page_size: 500 }); people.value = (p.items || []).map((x) => ({ id: x.id, name: x.name })) } catch (e) {}
  try { const r = await listInstruments({ page: 1, page_size: 1000 }); instByCode.value = Object.fromEntries((r.items || []).map((x) => [x.dept_no, x])) } catch (e) {}
  try { const m = await listPostInstrumentMap({ page: 1, page_size: 300 }); postMap.value = m.items || [] } catch (e) {}
})
async function refresh() {
  loading.value = true
  try { const r = await listAuthSheet({ page: 1, page_size: 500 }); list.value = r.items || [] } finally { loading.value = false }
}

function onNameChange(name) {
  const p = people.value.find((x) => x.name === name)
  form.value.person_id = p ? p.id : null
}
function onPostChange() {
  const codes = new Set(instOptions.value.map((i) => i.code))
  instCodes.value = instCodes.value.filter((c) => codes.has(c))
}
watch(instCodes, async () => {
  const names = []
  for (const c of instCodes.value) {
    let pj = projCache.get(c)
    if (pj === undefined) {
      pj = []
      const db = instByCode.value[c]
      if (db) {
        try {
          const items = await getInstrumentTestItems(db.id)
          pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim())
        } catch (e) { pj = [] }
      }
      projCache.set(c, pj)
    }
    names.push(...pj)
  }
  projText.value = [...new Set(names)].join('、')
  form.value.project = projText.value
})

function calcValid() {
  const d = (form.value.auth_date || '').trim()
  form.value.valid_from = form.value.valid_from || d
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) {
    const dt = new Date(d)
    form.value.valid_until = `${dt.getFullYear() + 1}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
  }
}

function openForm(row) {
  if (row) {
    form.value = { ...blank(), ...row }
    posts.value = [...postsOf(row)]
    instCodes.value = (row.instruments_json || []).map((i) => i.code || i)
    scopes.value = [...scopesOf(row)]
    projText.value = row.project || ''
  } else {
    form.value = blank(); posts.value = []; instCodes.value = []; scopes.value = []; projText.value = ''
  }
  visible.value = true
}
async function save() {
  try {
    const picked = instOptions.value.filter((i) => instCodes.value.includes(i.code))
    const payload = {
      ...form.value,
      posts_json: posts.value,
      instruments_json: picked,
      scopes_json: scopes.value,
      post: posts.value.join('、'),
      instrument: picked.map((i) => i.name).join('、'),
      auth_scope: scopes.value.join('、'),
      project: projText.value,
    }
    if (payload.id) await updateAuthSheet(payload.id, payload)
    else await createAuthSheet(payload)
    ElMessage.success('已保存'); visible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm(`删除「${row.name}」的授权记录？`, '提示', { type: 'warning' }); await deleteAuthSheet(row.id); ElMessage.success('已删除'); refresh() } catch (e) {}
}

async function openDetail(row) {
  current.value = await getAuthSheet(row.id)
  detailVisible.value = true
  detailProj.value = ''
  const names = []
  for (const i of current.value.instruments_json || []) {
    let pj = projCache.get(i.code)
    if (pj === undefined) {
      pj = []
      const db = instByCode.value[i.code]
      if (db) {
        try {
          const items = await getInstrumentTestItems(db.id)
          pj = (items || []).map((t) => `${t.code || ''} ${t.name || ''}`.trim())
        } catch (e) { pj = [] }
      }
      projCache.set(i.code, pj)
    }
    names.push(...pj)
  }
  detailProj.value = [...new Set(names)].join('、') || current.value.project || '（无关联项目）'
}

function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }
function printRow(row) {
  const html = `
  <h2 style="text-align:center;letter-spacing:3px;">检验科生化免疫组 人员授权书</h2>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td style="width:90px;text-align:center;background:#f7f7f7;">姓名</td><td style="width:150px;">${esc(row.name)}</td><td style="width:90px;text-align:center;background:#f7f7f7;">部门</td><td>${esc(row.department)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">授权岗位</td><td colspan="3">${esc(postsOf(row).join('、'))}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">授权仪器</td><td colspan="3">${esc(instNames(row).join('、') || row.instrument)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">授权权限</td><td colspan="3">${esc(scopesOf(row).join('、') || row.auth_scope)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">项目/方法</td><td colspan="3" style="font-size:11px;">${esc(row.project)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">有效期</td><td colspan="3">${esc(row.valid_from)} ~ ${esc(row.valid_until)}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">授权人</td><td>${esc(row.authorizer)}</td><td style="text-align:center;background:#f7f7f7;">资质</td><td>${esc(row.authorizer_qualification)}</td></tr>
  </table>
  <div style="margin-top:24px;text-align:right;">授权人签字：　　　　　　日期：　　　　</div>`
  printHtml('人员授权书', html)
}
</script>
