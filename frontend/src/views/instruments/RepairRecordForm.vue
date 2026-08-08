<template>
  <el-form class="repair-form" label-width="120px" label-position="right">
    <el-row :gutter="12">
      <el-col :span="12" :xs="24">
        <el-form-item label="发现人">
          <el-input v-model="form.finder" :placeholder="finderPlaceholder || '发现人姓名'" />
        </el-form-item>
      </el-col>
      <el-col :span="12" :xs="24">
        <el-form-item label="发现时间">
          <el-date-picker v-model="form.found_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择日期+时间" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="24">
        <el-form-item label="故障描述">
          <el-input v-model="form.fault_desc" type="textarea" :rows="2" placeholder="请详细描述故障内容" />
        </el-form-item>
      </el-col>
      <el-col :span="24">
        <el-form-item label="影响项目">
          <el-input v-model="form.affected_items" type="textarea" :rows="2" placeholder="列出受影响的具体项目（多个用逗号/换行分隔）" />
        </el-form-item>
      </el-col>
      <el-col :span="12" :xs="24">
        <el-form-item label="通知维修时间">
          <el-date-picker v-model="form.notify_repair_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="12" :xs="24">
        <el-form-item label="处理时间">
          <el-date-picker v-model="form.handled_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
      </el-col>
      <el-col :span="24">
        <el-form-item label="故障原因及维修过程">
          <el-input v-model="form.cause_process" type="textarea" :rows="3" placeholder="详细说明故障处理办法、处理结果及完成时间" />
        </el-form-item>
      </el-col>
      <el-col :span="12" :xs="24">
        <el-form-item label="维修人">
          <el-input v-model="form.repairer" placeholder="维修人姓名" />
        </el-form-item>
      </el-col>
      <el-col :span="12" :xs="24">
        <el-form-item label="恢复使用时间">
          <el-date-picker v-model="form.restored_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <el-divider content-position="left">排查后质控验证</el-divider>
    <el-form-item label="验证方式">
      <el-select v-model="qd.method" style="width: 260px">
        <el-option label="室内质控验证（默认）" value="qc" />
        <el-option label="样本比对" value="compare" />
        <el-option label="校准验证" value="calibrate" />
      </el-select>
    </el-form-item>

    <!-- 室内质控验证：项目 + 1~3 行 靶值/检测结果/在控与否 -->
    <template v-if="qd.method === 'qc'">
      <el-form-item label="项目">
        <el-input v-model="qd.qc.project" placeholder="如 ALT" style="width: 260px" />
      </el-form-item>
      <el-table :data="qd.qc.rows" border size="small" style="max-width: 780px">
        <el-table-column type="index" label="序号" width="55" align="center" />
        <el-table-column label="靶值">
          <template #default="{ row }"><el-input v-model="row.target" placeholder="靶值" /></template>
        </el-table-column>
        <el-table-column label="检测结果">
          <template #default="{ row }"><el-input v-model="row.result" placeholder="检测结果" /></template>
        </el-table-column>
        <el-table-column label="在控与否" width="130">
          <template #default="{ row }">
            <el-select v-model="row.control" placeholder="选择" style="width: 100%">
              <el-option label="在控" value="在控" />
              <el-option label="否" value="否" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column width="70" align="center">
          <template #default="{ $index }">
            <el-button v-if="qd.qc.rows.length > 1" link type="danger" @click="qd.qc.rows.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button v-if="qd.qc.rows.length < 3" size="small" style="margin-top:6px" @click="qd.qc.rows.push({ target: '', result: '', control: '' })">+ 添加一行（最多 3 行）</el-button>
    </template>

    <!-- 样本比对：项目 + 5 行 样本值/维修后结果/相对偏倚自动/可接受与否 -->
    <template v-if="qd.method === 'compare'">
      <el-form-item label="项目">
        <el-input v-model="qd.compare.project" placeholder="如 ALT" style="width: 260px" />
      </el-form-item>
      <el-table :data="qd.compare.rows" border size="small" style="max-width: 900px">
        <el-table-column type="index" label="序号" width="55" align="center" />
        <el-table-column label="样本值">
          <template #default="{ row }"><el-input v-model="row.sample" placeholder="样本值" /></template>
        </el-table-column>
        <el-table-column label="维修后检测结果">
          <template #default="{ row }"><el-input v-model="row.result" placeholder="检测结果" /></template>
        </el-table-column>
        <el-table-column label="相对偏倚（自动）" width="150" align="center">
          <template #default="{ row }">{{ calcBias(row) || '—' }}</template>
        </el-table-column>
        <el-table-column label="可接受与否" width="140">
          <template #default="{ row }">
            <el-select v-model="row.accept" placeholder="选择" style="width: 100%">
              <el-option label="可接受" value="可接受" />
              <el-option label="否" value="否" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 校准验证：项目 + 靶值 + 不确定度 + 3 次结果，自动判断均值是否在靶值±不确定度 -->
    <template v-if="qd.method === 'calibrate'">
      <el-row :gutter="12">
        <el-col :span="8" :xs="24">
          <el-form-item label="项目"><el-input v-model="qd.calibrate.project" placeholder="如 ALT" /></el-form-item>
        </el-col>
        <el-col :span="8" :xs="24">
          <el-form-item label="校准品靶值"><el-input v-model="qd.calibrate.target" placeholder="靶值" /></el-form-item>
        </el-col>
        <el-col :span="8" :xs="24">
          <el-form-item label="不确定度"><el-input v-model="qd.calibrate.uncertainty" placeholder="如 ±2" /></el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8" :xs="24" v-for="i in 3" :key="i">
          <el-form-item :label="`第${i}次检测结果`">
            <el-input v-model="qd.calibrate.results[i - 1]" placeholder="检测结果" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="自动判断">
        <el-tag :type="calTagType">{{ calText }}</el-tag>
      </el-form-item>
    </template>

    <el-divider content-position="left">维修前结果影响评估</el-divider>
    <el-form-item label="是否影响维修前检测结果">
      <el-select v-model="qd.affect_before" style="width: 160px">
        <el-option label="否" :value="false" />
        <el-option label="是" :value="true" />
      </el-select>
    </el-form-item>
    <!-- 影响前 → 样本比对 -->
    <template v-if="qd.affect_before">
      <el-alert type="warning" :closable="false" show-icon style="max-width: 900px; margin-bottom: 8px"
        title="已影响维修前检测结果，请补充样本比对评估（至少 5 份标本重测，计算相对偏倚）" />
      <el-form-item label="项目（比对）">
        <el-input v-model="qd.affect_compare.project" placeholder="如 ALT" style="width: 260px" />
      </el-form-item>
      <el-table :data="qd.affect_compare.rows" border size="small" style="max-width: 900px">
        <el-table-column type="index" label="序号" width="55" align="center" />
        <el-table-column label="样本值（维修前）">
          <template #default="{ row }"><el-input v-model="row.sample" placeholder="样本值" /></template>
        </el-table-column>
        <el-table-column label="维修后检测结果">
          <template #default="{ row }"><el-input v-model="row.result" placeholder="检测结果" /></template>
        </el-table-column>
        <el-table-column label="相对偏倚（自动）" width="150" align="center">
          <template #default="{ row }">{{ calcBias(row) || '—' }}</template>
        </el-table-column>
        <el-table-column label="可接受与否" width="140">
          <template #default="{ row }">
            <el-select v-model="row.accept" placeholder="选择" style="width: 100%">
              <el-option label="可接受" value="可接受" />
              <el-option label="否" value="否" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-form-item label="签字（恢复使用授权人）" style="margin-top: 8px">
      <el-input v-model="form.signer" :placeholder="signerPlaceholder || '默认登录人'" style="max-width: 300px" />
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, computed } from 'vue'
import { defaultQcDetail, mkQcRow, mkCmpRow } from '../../utils/repairQc'

const props = defineProps({
  form: { type: Object, required: true },
  finderPlaceholder: { type: String, default: '' },
  signerPlaceholder: { type: String, default: '' },
})

// ---------- 质控验证结构化数据 ----------
// form.qc_detail 不存在时自动补默认结构（响应式）
const qd = computed(() => {
  if (!props.form.qc_detail || typeof props.form.qc_detail !== 'object') {
    props.form.qc_detail = defaultQcDetail()
  }
  // 兼容旧数据缺子字段：逐级补默认
  const d = props.form.qc_detail
  d.qc = d.qc || { project: '', rows: [mkQcRow()] }
  d.compare = d.compare || { project: '', rows: Array.from({ length: 5 }, mkCmpRow) }
  d.calibrate = d.calibrate || { project: '', target: '', uncertainty: '', results: ['', '', ''] }
  d.affect_compare = d.affect_compare || { project: '', rows: Array.from({ length: 5 }, mkCmpRow) }
  if (!Array.isArray(d.qc.rows) || !d.qc.rows.length) d.qc.rows = [mkQcRow()]
  if (!Array.isArray(d.compare.rows) || !d.compare.rows.length) d.compare.rows = Array.from({ length: 5 }, mkCmpRow)
  if (!Array.isArray(d.affect_compare.rows) || !d.affect_compare.rows.length) d.affect_compare.rows = Array.from({ length: 5 }, mkCmpRow)
  if (!Array.isArray(d.calibrate.results)) d.calibrate.results = ['', '', '']
  return d
})

// 相对偏倚自动计算：(维修后 - 样本) / 样本 × 100%
function calcBias(row) {
  const s = parseFloat(row && row.sample)
  const r = parseFloat(row && row.result)
  if (isNaN(s) || isNaN(r) || s === 0) return ''
  return (((r - s) / s) * 100).toFixed(2) + '%'
}

// 校准验证自动判断：3 次均值是否在靶值 ± 不确定度
const calText = computed(() => {
  const c = qd.value.calibrate
  const vals = (c.results || []).map((v) => parseFloat(v)).filter((n) => !isNaN(n))
  const target = parseFloat(c.target)
  const unc = parseFloat(c.uncertainty)
  if (!vals.length) return '请填写校准品检测结果'
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  if (isNaN(target) || isNaN(unc)) return `均值 ${mean.toFixed(2)}（待填靶值 / 不确定度）`
  const ok = Math.abs(mean - target) <= unc
  return ok
    ? `3 次均值 ${mean.toFixed(2)}，在靶值±不确定度范围内 → 可接受`
    : `3 次均值 ${mean.toFixed(2)}，超出靶值±不确定度范围 → 否`
})
const calTagType = computed(() => {
  const t = calText.value
  if (t.includes('可接受')) return 'success'
  if (t.startsWith('3 次均值')) return 'danger'
  return 'info'
})

defineExpose({ defaultQcDetail, calcBias })
</script>
