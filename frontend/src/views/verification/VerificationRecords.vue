<template>
  <div class="vrec-page">
    <div class="vrec-toolbar">
      <span class="vrec-count">共 {{ rows.length }} 份验证报告</span>
      <el-button :loading="loading" @click="loadList">刷新</el-button>
    </div>

    <div v-for="r in rows" :key="r.id" class="vrec-item">
      <div class="vrec-head" @click="r._open = !r._open">
        <div class="vrec-info">
          <el-tag :type="r.report_type === 'qualitative' ? 'warning' : 'primary'" size="small" style="margin-right:8px">
            {{ r.report_type === 'qualitative' ? '定性' : '定量' }}
          </el-tag>
          <b class="vrec-name">{{ r.project_name || '未命名' }}</b>
          <span class="vrec-meta">{{ r.instrument_model || '' }} {{ r.instrument_no || '' }}</span>
          <span class="vrec-date">{{ r.verify_date || r.eval_date || '' }}</span>
        </div>
        <div class="vrec-actions">
          <el-tag v-if="r.report_file_path" type="success" size="small" effect="plain">已归档</el-tag>
          <el-tag v-else type="info" size="small" effect="plain">未生成</el-tag>
          <el-button size="small" @click.stop="r._open = !r._open">{{ r._open ? '收起' : '展开' }}</el-button>
          <el-button v-if="r.report_file_path" size="small" type="success" @click.stop="downloadReport(r)">下载报告</el-button>
          <el-button size="small" type="primary" plain @click.stop="generateIfNeeded(r)">生成报告</el-button>
          <el-button size="small" type="danger" plain @click.stop="del(r)">删除</el-button>
        </div>
      </div>

      <!-- 验证结论大表 -->
      <div v-if="r._open" class="vrec-detail">
        <div class="vrec-summary-title">验证结论汇总 — {{ r.project_name }}</div>

        <!-- 项目信息表 -->
        <el-descriptions :column="3" border size="small" style="margin-bottom:14px">
          <el-descriptions-item label="项目名称">{{ r.project_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="项目方法">{{ r.project_method || '—' }}</el-descriptions-item>
          <el-descriptions-item label="报告单位">{{ r.unit || '—' }}</el-descriptions-item>
          <el-descriptions-item label="仪器型号">{{ r.instrument_model || '—' }}</el-descriptions-item>
          <el-descriptions-item label="仪器编号">{{ r.instrument_no || '—' }}</el-descriptions-item>
          <el-descriptions-item v-if="r.report_type === 'quantitative'" label="允许总误差(TEA)">{{ teaPct(r.tea) }}</el-descriptions-item>
          <el-descriptions-item label="试剂厂家">{{ r.reagent || '—' }}</el-descriptions-item>
          <el-descriptions-item label="试剂批号">{{ r.reagent_lot || '—' }}</el-descriptions-item>
          <el-descriptions-item label="校准品">{{ r.calibrator || '—' }}</el-descriptions-item>
          <el-descriptions-item label="校准品批号">{{ r.calibrator_lot || '—' }}</el-descriptions-item>
          <el-descriptions-item label="质控品">{{ r.qc || '—' }}</el-descriptions-item>
          <el-descriptions-item label="质控品批号">{{ r.qc_lot || '—' }}</el-descriptions-item>
          <el-descriptions-item label="操作人员">{{ r.operator || '—' }}</el-descriptions-item>
          <el-descriptions-item label="审核人员">{{ r.reviewer || '—' }}</el-descriptions-item>
          <el-descriptions-item label="验证日期">{{ r.verify_date || '—' }}</el-descriptions-item>
          <el-descriptions-item v-if="r.report_type === 'quantitative'" label="声称线性范围">{{ r.linear_low || '—' }} ~ {{ r.linear_high || '—' }}{{ r.unit ? ' ' + r.unit : '' }}</el-descriptions-item>
          <el-descriptions-item v-if="r.report_type === 'quantitative'" label="稀释倍数">{{ r.dilution || '—' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 验证结论大表（截图2样式） -->
        <el-table :data="conclusionRows(r)" border stripe size="small">
          <el-table-column label="验证内容" width="140">
            <template #default="{ row }">{{ row.content }}</template>
          </el-table-column>
          <el-table-column label="验证要求" min-width="220">
            <template #default="{ row }">{{ row.requirement }}</template>
          </el-table-column>
          <el-table-column label="验证结果" min-width="180">
            <template #default="{ row }">
              <div style="white-space:pre-line">{{ row.result || '—' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="验证结论" width="110" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.conclusion" :type="row.conclusion.includes('符合') || row.conclusion === '合格' ? 'success' : 'danger'" size="small">
                {{ row.conclusion }}
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 总结论（排除 parser 误把模板段落标题"四、评价结论"等当正文的情况） -->
        <div v-if="conclusionText(r)" class="vrec-footer-note">
          <b>总结论：</b>{{ conclusionText(r) }}
        </div>

        <!-- 原始数据折叠 -->
        <el-collapse style="margin-top:8px" v-if="r.data">
          <el-collapse-item title="查看录入数据（JSON）" name="raw">
            <pre class="vrec-json">{{ formatData(r.data) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
    <el-empty v-if="!loading && !rows.length" description="暂无性能验证报告记录" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listVerificationReports, deleteVerificationReport, generateVerificationReport, downloadVerificationReport } from '../../api/verificationReports'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const rows = ref([])
const loading = ref(false)

const requirements = {
  qualitative: {
    precision1: '批内CV ≤7.5%',
    precision2: '实验室内CV ≤10.0%',
    conformity1: '阳性符合率≥95%',
    conformity2: '阴性符合率≥95%',
    lod: '检出限浓度的样品阳性率≥95%',
    specificity: '抗干扰能力符合厂家声明',
    reference: '参考范围验证通过',
  },
  quantitative: {
    precision1: '批内CV ≤1/4 TEA',
    precision2: '实验室内CV ≤1/3 TEA',
    trueness: '相对偏倚≤1/2 TEA',
    linearity: '各浓度点相对偏倚≤1/2 TEA，符合线性或临床可接受非线性',
    reportable1: '低限 ≤ TEA',
    reportable2: '高限 ≤1/2 TEA',
    reference: '每组超出参考区间不多于2个',
    specificity: '抗干扰能力符合厂家声明',
  },
}

function conclusionRows(r) {
  const rs = r.result_summary || {}
  const t = r.report_type || 'qualitative'
  const req = requirements[t] || requirements.qualitative
  // 本地副本：每个 record 单独算 TEA 倍数（避免污染模块级 requirements）
  const reqLocal = {}
  for (const k in req) reqLocal[k] = expandTea(req[k], r.tea)
  const items = []
  const unitSuffix = r.unit ? ' ' + r.unit : ''
  // 结果文本由后端计算引擎统一格式化（前缀/单位/合并范围/稀释逻辑），前端仅原样展示，避免重复加前缀
  const addRow = (content, key, requirement) => {
    const item = rs[key] || {}
    const result = item.result || ''
    const conclusion = item.conclusion || ''
    if (!result && !conclusion) return
    items.push({ content, requirement: requirement != null ? requirement : (reqLocal[key] || '—'), result, conclusion })
  }
  if (t === 'qualitative') {
    addRow('精密度', 'precision1', reqLocal['precision1'] || '—')
    addRow('精密度', 'precision2', reqLocal['precision2'] || '—')
    if (r.verify_items?.includes('conformity')) { addRow('方法符合率', 'conformity1'); addRow('方法符合率', 'conformity2') }
    if (r.verify_items?.includes('lod')) addRow('方法检出限', 'lod')
  } else {
    addRow('精密度', 'precision1', reqLocal['precision1'] || '—')
    addRow('精密度', 'precision2', reqLocal['precision2'] || '—')
    if (r.verify_items?.includes('trueness')) addRow('正确度', 'trueness')
    if (r.verify_items?.includes('linearity')) addRow('线性', 'linearity')
    if (r.verify_items?.includes('reportable')) {
      const rep = rs['reportable'] || {}
      const reqText = (r.dilution === '/') ? '等同线性范围' : `${reqLocal['reportable1'] || '—'} / ${reqLocal['reportable2'] || '—'}`
      if (rep.result || rep.conclusion) {
        addRow('可报告范围', 'reportable', reqText)
      } else {
        // 旧数据回退：合并 reportable1/reportable2（去掉 低限/高限 前缀）
        const r1 = rs['reportable1'] || {}, r2 = rs['reportable2'] || {}
        const low = (r1.result || '').replace(/^低限\s*/, '').trim()
        const high = (r2.result || '').replace(/^高限\s*/, '').trim()
        let result = '', cons = ''
        if (low && high) {
          result = `${low}-${high}${unitSuffix}`
          cons = (r1.conclusion && r2.conclusion) ? (r1.conclusion === r2.conclusion ? r1.conclusion : `${r1.conclusion}/${r2.conclusion}`) : (r1.conclusion || r2.conclusion || '')
        } else if (low) {
          result = `${low}${unitSuffix}`; cons = r1.conclusion || ''
        } else if (high) {
          result = `${high}${unitSuffix}`; cons = r2.conclusion || ''
        } else if (r.dilution === '/') {
          result = `${r.linear_low || ''}-${r.linear_high || ''}${unitSuffix}`; cons = '无'
        }
        if (result || cons) items.push({ content: '可报告范围', requirement: reqText, result, conclusion: cons })
      }
    }
  }
  if (r.verify_items?.includes('reference')) addRow('参考区间', 'reference')
  if (r.verify_items?.includes('specificity')) addRow('分析特异性', 'specificity')
  return items
}

function formatData(d) { try { return JSON.stringify(d, null, 2) } catch { return String(d) } }

// 总结论：parser 偶发把模板段落标题"四、评价结论"等当正文存进去，统一过滤
function conclusionText(r) {
  const t = (r?.conclusion || '').trim()
  if (!t) return ''
  if (/^[一二三四五六七八九十]+、/.test(t)) return ''
  return t
}

// 允许总误差：源数据是小数形式（如 0.18 = 18%），显示转为百分数
function teaPct(t) {
  if (t == null || t === '' || t === '—') return '—'
  const s = String(t).trim().replace('%', '')
  const v = parseFloat(s)
  if (isNaN(v)) return String(t)
  // 0<v<1 视为小数比例（0.18 → 18%）；>=1 直接当百分数
  const pct = v > 0 && v < 1 ? v * 100 : v
  return pct.toFixed(1) + '%'
}

// 把 requirement 里的 "≤ 1/4 TEA" / "≤ TEA" 等替换成 "≤ 1/4 TEA（5%）"（按 TEA% 算倍数）
function expandTea(reqText, teaStr) {
  if (!reqText || !teaStr) return reqText
  const s = String(teaStr).trim().replace('%', '')
  const teaVal = parseFloat(s)
  if (isNaN(teaVal) || teaVal <= 0) return reqText
  const pctNum = teaVal > 0 && teaVal < 1 ? teaVal * 100 : teaVal
  // 匹配 ≤ 1/4 TEA / ≤ 1/3 TEA / ≤ 1/2 TEA / ≤ TEA（无分数，即整倍 TEA）
  return reqText.replace(/≤\s*(\d+)?\s*(?:\/\s*(\d+))?\s*TEA/g, (m, num, den) => {
    const n = num ? parseInt(num) : 1
    const d = den ? parseInt(den) : 1
    const v = pctNum * n / d
    const s2 = String(parseFloat(v.toFixed(2)))
    return `${m}（${s2}%）`
  })
}

async function loadList() {
  loading.value = true
  try {
    const res = await listVerificationReports({ page_size: 300 })
    const data = Array.isArray(res) ? res : (res.items || [])
    data.forEach(r => { if (r._open === undefined) r._open = false })
    rows.value = data
  } catch (e) {
    ElMessage.error('加载失败')
  } finally { loading.value = false }
}

async function generateIfNeeded(r) {
  if (r.report_file_path) return
  try {
    await generateVerificationReport(r.id)
    ElMessage.success('报告已生成')
    await loadList()
  } catch (e) {
    ElMessage.error('生成失败：' + (e?.response?.data?.detail || e?.message))
  }
}

async function downloadReport(r) {
  try {
    const blob = await downloadVerificationReport(r.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `${r.project_name || '项目'}_性能验证.xlsx`; a.click()
    URL.revokeObjectURL(url)
  } catch (e) { ElMessage.error('下载失败') }
}

async function del(r) {
  await ElMessageBox.confirm(`确认删除「${r.project_name}」？`, '提示', { type: 'warning' })
  await deleteVerificationReport(r.id)
  ElMessage.success('已删除')
  await loadList()
}

onMounted(loadList)
</script>

<style scoped>
.vrec-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.vrec-count { color: #606266; font-size: 13px; }
.vrec-item { margin-bottom: 10px; border: 1px solid #e4e7ed; border-radius: 10px; overflow: hidden; }
.vrec-head { display: flex; justify-content: space-between; align-items: center; background: #f7fafc; padding: 10px 14px; cursor: pointer; user-select: none; }
.vrec-head:hover { background: #edf2f7; }
.vrec-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.vrec-name { font-size: 15px; color: #2d3748; }
.vrec-meta { font-size: 12px; color: #718096; }
.vrec-date { font-size: 12px; color: #a0aec0; }
.vrec-actions { display: flex; align-items: center; gap: 6px; }
.vrec-detail { padding: 14px; background: #fff; }
.vrec-summary-title { font-size: 15px; font-weight: 700; color: #1a202c; margin-bottom: 14px; border-bottom: 2px solid #409eff; padding-bottom: 6px; }
.vrec-footer-note { margin-top: 12px; padding: 10px; background: #f0f9ff; border: 1px solid #b8daff; border-radius: 6px; font-size: 13px; }
.vrec-json { background: #1a202c; color: #e2e8f0; padding: 12px; border-radius: 6px; font-size: 12px; max-height: 400px; overflow: auto; }
</style>
