<template>
  <div class="print-root" v-if="data">
    <!-- ============ 第 1 页：原表（BG-KS-PX-808） ============ -->
    <div class="page">
      <h1 class="doc-title">人员能力评估记录表（操作人员）</h1>
      <div class="doc-no">表单编号：BG-KS-PX-808</div>

      <table class="ptable head">
        <tr>
          <th>姓名</th><td>{{ d.name || '—' }}</td>
          <th>所在部门</th><td>{{ d.department || '—' }}</td>
          <th>年份</th><td>{{ d.year || '—' }}</td>
        </tr>
        <tr>
          <th>岗位</th><td colspan="3" class="left">{{ d.post || '—' }}</td>
          <th>评估日期</th><td>{{ d.assess_date || '—' }}</td>
        </tr>
      </table>

      <table class="ptable score">
        <thead>
          <tr>
            <th style="width:44px">序号</th>
            <th>评估项目</th>
            <th style="width:60px">满分</th>
            <th style="width:60px">得分</th>
          </tr>
        </thead>
        <tbody v-for="grp in groups" :key="grp.title">
          <tr class="grp-row">
            <th colspan="4" class="left">{{ grp.title }}（满分 {{ grp.weight }} 分，实得 {{ grpSum(grp) }} 分）</th>
          </tr>
          <tr v-for="it in grp.items" :key="it">
            <td>{{ no(it) }}</td>
            <td class="left">{{ it }}</td>
            <td>5</td>
            <td>{{ score(it) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <th colspan="2">合计（≥80 分为合格）</th>
            <th>100</th>
            <th>{{ d.total || 0 }}</th>
          </tr>
          <tr>
            <th colspan="2">评估结论</th>
            <th colspan="2">{{ d.conclusion || verdict }}</th>
          </tr>
        </tfoot>
      </table>

      <table class="ptable head">
        <tr><th>备注</th><td colspan="5" class="left">{{ d.remark || '—' }}</td></tr>
      </table>

      <div class="psign">
        <span>评估人：{{ d.assessor || '　　　　　' }}</span>
        <span>授权人：{{ d.authorizer || '　　　　　' }}</span>
        <span>日期：{{ d.assess_date || '　　　　　' }}</span>
      </div>
    </div>

    <!-- ============ 第 2 页起：各项评估依据明细 ============ -->
    <div class="page">
      <h1 class="doc-title">人员能力评估依据明细（附页）</h1>
      <div class="doc-no">
        表单编号：BG-KS-PX-808 附页　　姓名：{{ d.name || '—' }}　　部门：{{ d.department || '—' }}　　岗位：{{ d.post || '—' }}　　年份：{{ d.year || '—' }}
      </div>

      <table class="ptable ev">
        <thead>
          <tr>
            <th style="width:40px">序号</th>
            <th style="width:168px">评估项目</th>
            <th style="width:44px">得分</th>
            <th style="width:98px">评估方法</th>
            <th>依据描述</th>
            <th style="width:104px">关联编号</th>
            <th style="width:72px">日期</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in allItems" :key="it">
            <td>{{ i + 1 }}</td>
            <td class="left">{{ it }}</td>
            <td>{{ score(it) }}</td>
            <td>{{ methodLabel(ev(it).method) || '—' }}</td>
            <td class="left">{{ ev(it).evidence || '—' }}</td>
            <td>{{ ev(it).ref_id || '—' }}</td>
            <td>{{ ev(it).date || d.assess_date || '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="psummary">评估方法统计：{{ methodSummary }}</div>

      <div class="psign">
        <span>评估人：{{ d.assessor || '　　　　　' }}</span>
        <span>审核/授权人：{{ d.authorizer || '　　　　　' }}</span>
        <span>日期：{{ d.assess_date || '　　　　　' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { groups, allItems, methodLabel, defaultEvidence } from './competencyMeta'

const props = defineProps({ data: { type: Object, default: null } })
const d = computed(() => props.data || {})
const scores = computed(() => d.value.scores_json || {})
const evidences = computed(() => d.value.evidence_json || {})

function score(it) {
  const v = scores.value[it]
  return v == null ? 0 : Number(v)
}
function ev(it) {
  const e = evidences.value[it]
  return e ? { ...defaultEvidence(it), ...e } : defaultEvidence(it)
}
function no(it) { return allItems.indexOf(it) + 1 }
function grpSum(grp) { return grp.items.reduce((a, it) => a + score(it), 0) }

const verdict = computed(() => (Number(d.value.total) >= 80 ? '合格' : '不合格'))
const methodSummary = computed(() => {
  const m = {}
  allItems.forEach((it) => {
    const k = methodLabel(ev(it).method) || '未指定'
    m[k] = (m[k] || 0) + 1
  })
  return Object.entries(m).map(([k, v]) => `${k} ${v} 项`).join('　　')
})
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
.print-root .ptable.score thead th { background: #f2f2f2; }
.print-root .ptable.score tbody th.grp-row th,
.print-root .ptable.score tr.grp-row th { background: #e8f0fb; text-align: left; }
.print-root .ptable.score tfoot th { background: #f2f2f2; }
.print-root .ptable.ev thead th { background: #f2f2f2; }
.print-root .psummary {
  font-size: 12px; margin: 4px 0 16px;
  font-family: "宋体", "SimSun", serif;
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
  /* 第 1 页原表，其后每页为附页 */
  .print-root .page { page-break-before: always; }
  .print-root .page:first-child { page-break-before: avoid; }
  .print-root .ptable.ev tr { page-break-inside: avoid; }
}
</style>
