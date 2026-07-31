<template>
  <div class="print-root" v-if="data">
    <h1 class="doc-title">生免室新员工培训及考核表</h1>
    <div class="doc-no">表单编号：BG-SM-PX-005</div>

    <table class="ptable head">
      <tr>
        <th>员工姓名</th><td>{{ d.name }}</td>
        <th>员工类别</th><td>{{ d.employee_category }}</td>
        <th>培训专业</th><td>{{ d.train_major }}</td>
      </tr>
      <tr>
        <th>入组时间</th><td>{{ d.group_join_date }}</td>
        <th>培训时长</th><td colspan="3">{{ d.train_duration }}</td>
      </tr>
    </table>

    <div class="psec">一、能力评估（生化、免疫各一次）</div>
    <table class="ptable">
      <tr><th class="lab">评估项目</th><th>生化评估</th><th>免疫评估</th><th>理论 / 操作 / 口试</th></tr>
      <tr><th class="lab">评估结果</th><td>{{ d.ability_bio_result }}</td><td>{{ d.ability_immuno_result }}</td><td>{{ d.theory_operation_oral_result }}</td></tr>
      <tr><th class="lab">评估负责人</th><td>{{ d.ability_bio_responsible }}</td><td>{{ d.ability_immuno_responsible }}</td><td>—</td></tr>
    </table>

    <div class="psec">二、考核结果</div>
    <table class="ptable">
      <tr>
        <th class="lab">考核时间</th><td>{{ d.exam_time }}</td>
        <th class="lab">考核结果</th><td>{{ d.exam_result }}</td>
        <th class="lab">考核负责人</th><td>{{ d.exam_responsible }}</td>
      </tr>
    </table>

    <div class="psec">三、培训计划及考核内容</div>
    <table class="ptable plan">
      <thead>
        <tr>
          <th style="width:36px">序号</th>
          <th style="width:78px">培训类别</th>
          <th>培训内容</th>
          <th style="width:78px">培训老师</th>
          <th style="width:100px">培训方式</th>
          <th style="width:100px">考核方式</th>
          <th style="width:100px">考核成绩</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(it, i) in planItems" :key="i">
          <td>{{ i + 1 }}</td>
          <td>{{ it.category }}</td>
          <td class="left">{{ it.content }}</td>
          <td>{{ it.teacher }}</td>
          <td>{{ join(it.method) }}</td>
          <td>{{ join(it.exam_method) }}</td>
          <td>{{ it.score !== '' && it.score != null ? it.score + '（' + pScoreVerdict(it.score) + '）' : '—' }}</td>
        </tr>
        <tr v-if="!planItems.length"><td colspan="7" class="left">（无培训计划）</td></tr>
      </tbody>
    </table>

    <div class="psign">
      <span>制表人：____________</span>
      <span>审核人：____________</span>
      <span>日期：______年____月____日</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })
const d = computed(() => props.data || {})
const planItems = computed(() => Array.isArray(props.data?.plan_items) ? props.data.plan_items : [])

function join(v) {
  if (Array.isArray(v)) return v.filter(Boolean).join('、')
  if (typeof v === 'string') return v
  return ''
}
// 考核成绩按 80 分自动判定合格与否
function pScoreVerdict(v) {
  if (v === '' || v === null || v === undefined) return ''
  const n = typeof v === 'number' ? v : parseFloat(String(v).trim())
  if (Number.isNaN(n)) return ''
  return n >= 80 ? '合格' : '不合格'
}
</script>

<style>
/* 屏幕态：打印区始终隐藏，仅打印时显示 */
.print-root { display: none; }

.print-root .doc-title {
  text-align: center; font-size: 20px; font-weight: bold;
  margin: 0 0 4px; font-family: "宋体", "SimSun", serif;
}
.print-root .doc-no {
  text-align: center; font-size: 12px; color: #555;
  margin-bottom: 12px; font-family: "宋体", "SimSun", serif;
}
.print-root .ptable {
  width: 100%; border-collapse: collapse; margin-bottom: 14px;
  font-size: 12px; font-family: "宋体", "SimSun", serif;
}
.print-root .ptable th, .print-root .ptable td {
  border: 1px solid #333; padding: 5px 8px; text-align: center;
}
.print-root .ptable th.lab { background: #f2f2f2; width: 96px; }
.print-root .ptable.head th { width: 96px; background: #f2f2f2; }
.print-root .ptable .left { text-align: left; }
.print-root .ptable.plan th { background: #f2f2f2; }
.print-root .psec {
  font-weight: bold; font-size: 13px; margin: 12px 0 5px;
  font-family: "黑体", "SimHei", sans-serif;
}
.print-root .psign {
  margin-top: 22px; display: flex; justify-content: space-between;
  font-size: 12px; font-family: "宋体", "SimSun", serif;
}

@media print {
  @page { size: A4; margin: 12mm; }
  /* print-root 已通过 Teleport 挂载到 body，直接隐藏其它 body 子元素即可，
     避免 visibility 叠加 + position:absolute 导致多页内容被裁掉。 */
  body > *:not(.print-root) { display: none !important; }
  .print-root {
    display: block !important;
    position: static !important;
    width: 100% !important;
    visibility: visible !important;
  }
  .print-root .ptable.plan tr { page-break-inside: avoid; }
}
</style>
