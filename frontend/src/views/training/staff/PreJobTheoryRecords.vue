<template>
  <div class="prejob-theory-records">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <div>
        <h2 class="title" style="margin:0;">岗前理论考核答题记录</h2>
        <span style="color:#666;font-size:12px;">扫码/在线答题每次提交独立归档，可查询、查看答卷明细、导出留存（理论考核归档用）</span>
      </div>
      <div style="display:flex;gap:8px;">
        <el-input v-model="kw" size="small" placeholder="搜索姓名" style="width:160px;" clearable @keyup.enter="refresh" />
        <el-button size="small" @click="refresh">查询</el-button>
        <el-button size="small" type="primary" plain @click="exportExcel" :disabled="!rows.length">导出 Excel</el-button>
      </div>
    </div>

    <el-table :data="rows" border size="small" v-loading="loading" max-height="620">
      <el-table-column type="index" label="序号" width="55" align="center" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column label="考核岗位" min-width="180">
        <template #default="{ row }">{{ (row.posts_json || []).join('、') }}</template>
      </el-table-column>
      <el-table-column label="百分制" width="90" align="center">
        <template #default="{ row }"><b>{{ row.score_pct }}</b> / 100</template>
      </el-table-column>
      <el-table-column label="原始分" width="90" align="center">
        <template #default="{ row }">{{ row.score_raw }} / {{ row.score_full }}</template>
      </el-table-column>
      <el-table-column prop="attempt_no" label="第几次" width="80" align="center" />
      <el-table-column label="来源" width="80" align="center">
        <template #default="{ row }">{{ srcLabel(row.source) }}</template>
      </el-table-column>
      <el-table-column prop="submit_at" label="提交时间" width="170">
        <template #default="{ row }">{{ fmt(row.submit_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">答卷明细</el-button>
          <el-button link type="primary" @click="printRow(row)">打印</el-button>
          <el-button link type="danger" :disabled="!canWrite" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailVisible" :title="'答卷明细 · ' + (current?.name || '')" width="900px" top="4vh">
      <div v-if="current" style="margin-bottom:8px;font-size:13px;color:#444;">
        提交时间：{{ fmt(current.submit_at) }}　|　第 {{ current.attempt_no }} 次作答　|　
        百分制：<b>{{ current.score_pct }}</b> / 100　|　原始分：{{ current.score_raw }} / {{ current.score_full }}
      </div>
      <div v-for="post in current?.posts_json || []" :key="post" style="margin-bottom:14px;">
        <h4 style="margin:6px 0;border-left:4px solid #2563eb;padding-left:8px;">
          {{ post }}　
          <span style="color:#666;font-weight:400;font-size:12px;">
            <template v-if="(current.detail_json || {})[post]?.full">
              得分 {{ (current.detail_json || {})[post]?.pct ?? 0 }} / 100（原始 {{ (current.detail_json || {})[post]?.score ?? 0 }}/{{ (current.detail_json || {})[post]?.full ?? 0 }}）
            </template>
            <template v-else>该岗位无理论考核（不计入百分制）</template>
          </span>
        </h4>
        <div v-for="q in questionsOf(post)" :key="q.key" style="margin-bottom:5px;font-size:12px;line-height:1.5;">
          <div>{{ q.seq }}. <span v-if="q.kind">[{{ q.kind }}]</span> {{ q.q }}</div>
          <div v-if="q.options" style="color:#666;">{{ q.options.join('　') }}</div>
          <div>被考核人选择：<b>{{ q.picked || '—' }}</b>　
            <span :style="{ color: q.ok ? '#16a34a' : '#dc2626' }">
              {{ q.picked ? (q.ok ? '✓ 正确' : '✗ 错误') : '（未作答）' }}
            </span>
            <span style="color:#888;">（正确答案：{{ q.answer }}）</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listPreJobTheoryRecords, deletePreJobTheoryRecord } from '../../../api/education'
import { printHtml } from '../../../utils/printHtml'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const rows = ref([])
const loading = ref(false)
const kw = ref('')
const detailVisible = ref(false)
const current = ref(null)

function fmt(v) {
  if (!v) return ''
  return String(v).replace('T', ' ').slice(0, 19)
}
const ansStr = (a) => (Array.isArray(a) ? a.join('') : String(a == null ? '' : a))
const srcLabel = (s) => ({ qr: '扫码', online: '在线', import: '导入' }[s] || s || '扫码')

async function refresh() {
  loading.value = true
  try {
    const res = await listPreJobTheoryRecords({ q: kw.value.trim() || undefined, page_size: 300 })
    rows.value = res.items || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally { loading.value = false }
}
onMounted(refresh)

function openDetail(row) {
  current.value = row
  detailVisible.value = true
}

// 组装某岗位的逐题明细（题干/选项来自试卷快照，作答来自 answers_json）
function questionsOf(post) {
  const paper = (current.value?.papers_json || {})[post] || {}
  const ans = (current.value?.answers_json || {})[post] || {}
  const out = []
  let seq = 1
  ;(paper.single || []).forEach((t, i) => {
    const picked = ansStr(ans['s' + i])
    const right = ansStr(t.answer)
    out.push({ key: 's' + i, seq: seq++, kind: '单选', q: t.q, options: t.options, answer: right, picked, ok: !!picked && picked === right.slice(0, 1) })
  })
  ;(paper.multi || []).forEach((t, i) => {
    const picked = ansStr(ans['m' + i])
    const right = ansStr(t.answer)
    out.push({ key: 'm' + i, seq: seq++, kind: '多选', q: t.q, options: t.options, answer: right, picked, ok: !!picked && picked.split('').sort().join('') === right.split('').sort().join('') })
  })
  ;(paper.judge || []).forEach((t, i) => {
    const picked = ansStr(ans['j' + i])
    const right = ansStr(t.answer)
    out.push({ key: 'j' + i, seq: seq++, kind: '判断', q: t.q, options: null, answer: right, picked, ok: !!picked && picked === right })
  })
  return out
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`删除「${row.name}」第 ${row.attempt_no} 次答题归档？`, '提示', { type: 'warning' })
    await deletePreJobTheoryRecord(row.id)
    ElMessage.success('已删除')
    refresh()
  } catch (e) { /* 取消 */ }
}

// 导出归档 Excel（含逐题作答）
async function exportExcel() {
  try {
    const ExcelJS = (await import('exceljs')).default || (await import('exceljs'))
    const wb = new ExcelJS.Workbook()
    const ws = wb.addWorksheet('答题归档')
    ws.columns = [
      { header: '姓名', key: 'name', width: 12 },
      { header: '考核岗位', key: 'posts', width: 28 },
      { header: '百分制', key: 'pct', width: 10 },
      { header: '原始分', key: 'raw', width: 12 },
      { header: '第几次', key: 'attempt', width: 10 },
      { header: '来源', key: 'source', width: 10 },
      { header: '提交时间', key: 'time', width: 20 },
      { header: '岗位得分明细', key: 'detail', width: 50 },
    ]
    rows.value.forEach((r) => {
      const detail = Object.entries(r.detail_json || {})
        .map(([k, v]) => (v.full ? `${k}: ${v.pct ?? 0}/100（${v.score ?? 0}/${v.full ?? 0}）` : `${k}: 无理论考核(不计入)`))
        .join('；')
      ws.addRow({
        name: r.name,
        posts: (r.posts_json || []).join('、'),
        pct: r.score_pct,
        raw: `${r.score_raw}/${r.score_full}`,
        attempt: r.attempt_no,
        source: srcLabel(r.source),
        time: fmt(r.submit_at),
        detail,
      })
    })
    const buf = await wb.xlsx.writeBuffer()
    const blob = new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `岗前理论考核答题记录_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success('已导出')
  } catch (e) {
    ElMessage.error('导出失败：' + (e?.message || e))
  }
}

function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }
function printRow(row) {
  const blocks = (row.posts_json || []).map((post) => {
    const d = (row.detail_json || {})[post] || {}
    const qs = questionsOf2(row, post)
    return `<h3 style="margin:10px 0 4px;">${esc(post)}　<span style="font-weight:400;font-size:12px;">
      ${d.full ? '得分 ' + (d.pct ?? 0) + ' / 100（原始 ' + (d.score ?? 0) + '/' + (d.full ?? 0) + '）' : '无理论考核（不计入）'}</span></h3>
      ${!d.full ? '<div style="font-size:12px;color:#888;">该岗位无理论考核（不计入百分制）</div>' : ''}
      ${qs.map((q) => `<div style="font-size:12px;margin-bottom:4px;">${q.seq}. ${esc(q.q)}<br/>
        <span style="color:#333;">被考核人选择：<b>${esc(q.picked || '—')}</b>　${q.picked ? (q.ok ? '✓ 正确' : '✗ 错误') : '（未作答）'}　（正确答案：${esc(q.answer)}）</span></div>`).join('')}`
  }).join('')
  const html = `
  <h2 style="text-align:center;letter-spacing:3px;margin:0 0 4px;">岗前理论考核答题记录</h2>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr><td style="width:90px;text-align:center;background:#f7f7f7;">姓名</td><td>${esc(row.name)}</td>
        <td style="width:90px;text-align:center;background:#f7f7f7;">提交时间</td><td>${esc(fmt(row.submit_at))}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">考核岗位</td><td colspan="3">${esc((row.posts_json || []).join('、'))}</td></tr>
    <tr><td style="text-align:center;background:#f7f7f7;">成绩</td><td colspan="3">百分制 <b>${row.score_pct}</b> / 100　（原始 ${row.score_raw}/${row.score_full}）　第 ${row.attempt_no} 次作答</td></tr>
  </table>
  ${blocks}
  <div style="margin-top:22px;text-align:center;font-size:13px;">被考核人签字：　　　　　　　考核人签字：　　　　　　　日期：</div>`
  printHtml('岗前理论考核答题记录', html)
}
function questionsOf2(row, post) {
  const paper = (row.papers_json || {})[post] || {}
  const ans = (row.answers_json || {})[post] || {}
  const out = []
  let seq = 1
  ;(paper.single || []).forEach((t, i) => {
    const picked = ansStr(ans['s' + i]); const right = ansStr(t.answer)
    out.push({ seq: seq++, q: t.q, answer: right, picked, ok: !!picked && picked === right.slice(0, 1) })
  })
  ;(paper.multi || []).forEach((t, i) => {
    const picked = ansStr(ans['m' + i]); const right = ansStr(t.answer)
    out.push({ seq: seq++, q: t.q, answer: right, picked, ok: !!picked && picked.split('').sort().join('') === right.split('').sort().join('') })
  })
  ;(paper.judge || []).forEach((t, i) => {
    const picked = ansStr(ans['j' + i]); const right = ansStr(t.answer)
    out.push({ seq: seq++, q: t.q, answer: right, picked, ok: !!picked && picked === right })
  })
  return out
}
</script>
