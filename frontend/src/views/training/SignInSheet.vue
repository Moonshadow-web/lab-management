<template>
  <div class="sign-in-sheet">
    <div class="no-print toolbar">
      <el-alert type="info" :closable="false" :title="`打印空白签到表 → 现场签名 → 扫描后上传到「签到扫描件」页签留存`">
        {{ tipText }}
        <div class="fe-ver">页面版本：FE {{ feChunk || '…' }} · BE {{ beMark || '…' }}（若与最新不符请强刷 Ctrl+F5）</div>
      </el-alert>
      <div class="sheet-actions">
        <el-button type="primary" :icon="Printer" @click="doPrint">打印空白签到表</el-button>
        <el-button :icon="Plus" @click="addRow">加一行</el-button>
        <el-button :icon="Delete" @click="clearRows" v-if="rows.length">清空</el-button>
      </div>
    </div>

    <!-- 屏显预览（打印时隐藏） -->
    <div class="sheet preview no-print" v-if="rows.length">
      <h2 class="sheet-title">{{ sheetTitle }}</h2>
      <!-- 科内培训（BG-KS-PX-807）：科室/日期/课程名称 一行三格 -->
      <table class="sheet-head" v-if="isKs">
        <tr>
          <td class="lbl">科室</td>
          <td>{{ header.department || '检验科' }}</td>
          <td class="lbl">日期</td>
          <td>{{ header.train_time || '　' }}</td>
          <td class="lbl">课程名称</td>
          <td>{{ header.name || '　' }}</td>
        </tr>
      </table>
      <table class="sheet-head" v-else>
        <tr>
          <td class="lbl">培训名称</td>
          <td>{{ header.name || '　' }}</td>
          <td class="lbl">培训老师</td>
          <td>{{ header.teacher || '　' }}</td>
        </tr>
        <tr>
          <td class="lbl">时间</td>
          <td>{{ header.train_time || '　' }}</td>
          <td class="lbl">地点</td>
          <td>{{ header.location || '　' }}</td>
        </tr>
        <tr>
          <td class="lbl">培训对象</td>
          <td colspan="3">{{ header.target || '　' }}</td>
        </tr>
      </table>
      <table class="sign-grid">
        <thead>
          <tr>
            <th>姓　名</th><th>职 称</th><th>签 到</th>
            <th>姓　名</th><th>职 称</th><th>签 到</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(pair, i) in pairedRows" :key="i">
            <template v-if="pair.left">
              <td>{{ pair.left.name }}</td><td>{{ pair.left.title }}</td><td class="sign-cell"></td>
            </template>
            <template v-else><td></td><td></td><td class="sign-cell"></td></template>
            <template v-if="pair.right">
              <td>{{ pair.right.name }}</td><td>{{ pair.right.title }}</td><td class="sign-cell"></td>
            </template>
            <template v-else><td></td><td></td><td class="sign-cell"></td></template>
          </tr>
        </tbody>
        <tfoot v-if="isKs">
          <tr><td colspan="6" class="sign-foot">科室负责人签字：＿＿＿＿＿＿＿＿＿＿</td></tr>
        </tfoot>
      </table>
    </div>

    <!-- 打印专用：Teleport 到 body，仅打印时显示，规避 el-dialog fixed 浮层打印空白 -->
    <Teleport to="body">
      <div class="print-root sheet" :class="isKs ? 'pr-ks' : 'pr-sm'" v-if="rows.length">
        <h2 class="sheet-title">{{ sheetTitle }}</h2>
        <table class="sheet-head" v-if="isKs">
          <tr>
            <td class="lbl">科室</td>
            <td>{{ header.department || '检验科' }}</td>
            <td class="lbl">日期</td>
            <td>{{ header.train_time || '　' }}</td>
            <td class="lbl">课程名称</td>
            <td>{{ header.name || '　' }}</td>
          </tr>
        </table>
        <table class="sheet-head" v-else>
          <tr>
            <td class="lbl">培训名称</td>
            <td>{{ header.name || '　' }}</td>
            <td class="lbl">培训老师</td>
            <td>{{ header.teacher || '　' }}</td>
          </tr>
          <tr>
            <td class="lbl">时间</td>
            <td>{{ header.train_time || '　' }}</td>
            <td class="lbl">地点</td>
            <td>{{ header.location || '　' }}</td>
          </tr>
          <tr>
            <td class="lbl">培训对象</td>
            <td colspan="3">{{ header.target || '　' }}</td>
          </tr>
        </table>
        <table class="sign-grid">
          <thead>
            <tr>
              <th>姓　名</th><th>职 称</th><th>签 到</th>
              <th>姓　名</th><th>职 称</th><th>签 到</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(pair, i) in pairedRows" :key="i">
              <template v-if="pair.left">
                <td>{{ pair.left.name }}</td><td>{{ pair.left.title }}</td><td class="sign-cell"></td>
              </template>
              <template v-else><td></td><td></td><td class="sign-cell"></td></template>
              <template v-if="pair.right">
                <td>{{ pair.right.name }}</td><td>{{ pair.right.title }}</td><td class="sign-cell"></td>
              </template>
              <template v-else><td></td><td></td><td class="sign-cell"></td></template>
            </tr>
          </tbody>
          <tfoot>
            <tr v-if="isKs"><td colspan="6" class="sign-foot">科室负责人签字：＿＿＿＿＿＿＿＿＿＿</td></tr>
            <tr><td colspan="6" class="foot-cell">{{ footText }}</td></tr>
          </tfoot>
        </table>
      </div>
    </Teleport>

    <div class="no-print">
      <el-divider content-position="left">编辑签到名单（打印前可调）</el-divider>
      <el-table :data="uniqueRows" border size="small">
        <el-table-column label="姓名" width="160">
          <template #default="{ row }">
            <el-input v-model="row.name" placeholder="姓名" />
          </template>
        </el-table-column>
        <el-table-column label="职称" width="160">
          <template #default="{ row }">
            <el-input v-model="row.title" placeholder="职称" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link type="danger" :icon="Delete" @click="removeRow(row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Printer, Plus, Delete } from '@element-plus/icons-vue'
import { listPersonnel } from '../../api/education'

const props = defineProps({
  ownerId: { type: [Number, String], required: true },
  header: { type: Object, default: () => ({}) },
  canWrite: { type: Boolean, default: true },
  // 已保存的签到名单（数组 [{name,title}]）；有则优先使用，避免手动改动丢失
  savedNames: { type: Array, default: null },
  // 版式：sm = 组内培训（BG-SM-PX-006，生化免疫组）；ks = 科内培训（BG-KS-PX-807，检验科）
  variant: { type: String, default: 'sm' },
})

const isKs = computed(() => props.variant === 'ks')
const sheetTitle = computed(() => (isKs.value ? '民航总医院检验科继续教育培训签到表' : '生化免疫组培训签到表'))
const footText = computed(() => (isKs.value
  ? '表格编号：BG-KS-PX-807　　民航总医院检验科　　生效日期：2025.04.01'
  : '表格编号：BG-SM-PX-006　　检验科生化免疫组　　生效日期：2026.9.1'))
const tipText = computed(() => (isKs.value
  ? '打印后手工签名，再将扫描件上传到「签到扫描件」页签，即完成 BG-KS-PX-807 签到表归档。'
  : '打印后手工签名，再将扫描件上传到上方"课件 / 通知 / 考题 / 效果评价 / 签到 存档"的「签到扫描件」页签，即完成 BG-SM-PX-006 签到表归档。'))

// BG-KS-PX-807 固定名单（检验科全科，取自已归档的签到表模板）
const KS_NAMES = [
  ['王学晶', ''], ['陈剑', ''], ['张鲲', ''], ['龚珂', ''], ['刘书理', ''], ['王广进', ''],
  ['赵华', ''], ['张妹', ''], ['徐晓琳', ''], ['尹海珊', ''], ['张莹', ''], ['郑蕊', ''],
  ['朱金曼', ''], ['梁音', ''], ['孙碧璇', ''], ['赵爽', ''], ['张贺然', ''], ['李东', ''],
  ['时琰丽', ''], ['王杉', ''], ['崔彦超', ''], ['王晓倩', ''], ['赵瑞', ''], ['高宏进文', ''],
  ['常昊宇', ''], ['陆雨晴', ''], ['吴英', ''], ['张岩', ''], ['杨静', ''], ['王春馨', ''],
  ['王淑华', ''], ['张婵媛', ''], ['姚建民', ''], ['贾国伟', ''], ['赵海元', ''], ['朱春阳', ''],
  ['郑飞', ''], ['夏立娇', ''], ['张洪顺', ''], ['秦东芳', ''], ['孔亚龙', ''], ['杨越屹', ''],
  ['李昊峻', ''], ['秦满红', ''], ['宋浩', ''], ['吴朋', ''], ['代鹏', ''], ['吕文娟', ''],
  ['金子铮', ''], ['赵慧君', ''], ['翟晓丹', ''],
]

const rows = ref([])
const feChunk = ref('')
const beMark = ref('')

// 显示浏览器实际执行的前端 chunk 与后端构建标记，便于确认是否为新版本
async function loadVersionTag() {
  try {
    const s = [...document.querySelectorAll('script[src]')].map((x) => x.src || '').find((x) => x.includes('StaffEducation'))
    feChunk.value = s ? s.split('/').pop().replace('.js', '') : '(未知)'
  } catch (e) { feChunk.value = '(未知)' }
  try {
    const base = (document.baseURI || location.origin).replace(/\/[^/]*$/, '')
    const res = await fetch(base + '/api/v1/_diag/build')
    const j = await res.json()
    beMark.value = j.build || ''
  } catch (e) { beMark.value = '(未知)' }
}
loadVersionTag()

// 渲染层强制去重：无论内存 rows 来源如何（预填/手动/历史残留），屏显与打印均不出现同名重复行
const uniqueRows = computed(() => {
  const seen = new Set()
  return rows.value.filter((r) => {
    const n = (r.name || '').trim()
    if (!n) return true
    if (seen.has(n)) return false
    seen.add(n)
    return true
  })
})

const pairedRows = computed(() => {
  const out = []
  for (let i = 0; i < uniqueRows.value.length; i += 2) {
    out.push({ left: uniqueRows.value[i], right: uniqueRows.value[i + 1] || null })
  }
  // 保证至少 26 行（一页即可容纳）
  while (out.length < 26) out.push({ left: null, right: null })
  return out
})

function addRow() { rows.value.push({ name: '', title: '' }) }
function removeRow(r) { rows.value = rows.value.filter((x) => x !== r) }
function clearRows() { rows.value = [] }

async function doPrint() {
  emitSaveHeader()
  // 只打印本组件这一张：给 body 打标记，打印样式据此只显示对应的 print-root
  document.body.dataset.printTarget = isKs.value ? 'ks' : 'sm'
  await new Promise((r) => setTimeout(r, 100))
  window.print()
  // 打印后复位，避免影响其它打印组件（能力评估/新员工培训等）
  delete document.body.dataset.printTarget
}

const emit = defineEmits(['save-header'])
function emitSaveHeader() {
  emit('save-header', { names: dedupeNames(uniqueRows.value.map((r) => ({ name: r.name, title: r.title }))) })
}

// 排除“培训老师”本人，并去重
function excludeTeacher(list) {
  const t = (props.header && props.header.teacher) || ''
  const seen = new Set()
  return (list || []).filter((p) => {
    const n = (p.name || '').trim()
    if (t && n === t) return false
    if (!n || seen.has(n)) return false
    seen.add(n)
    return true
  })
}

onMounted(async () => {
  if (props.savedNames && props.savedNames.length) {
    rows.value = dedupeNames(props.savedNames.map((n) => ({ name: n.name || '', title: n.title || '' })))
  } else if (isKs.value) {
    // 科内培训：用 BG-KS-PX-807 的检验科全科名单
    rows.value = KS_NAMES.map(([name, title]) => ({ name, title }))
  } else {
    try {
      const res = await listPersonnel({ page: 1, page_size: 200 })
      const people = (res.items || []).map((p) => ({ name: p.name, title: p.title }))
      rows.value = excludeTeacher(people)
    } catch (e) {}
  }
  if (!rows.value.length) addRow()
})

function dedupeNames(list) {
  const seen = new Set()
  return (list || []).filter((r) => {
    const n = (r.name || '').trim()
    if (!n || seen.has(n)) return false
    seen.add(n)
    return true
  })
}
</script>

<style scoped>
.sign-in-sheet { padding: 8px 0; }
.toolbar { margin-bottom: 12px; }
.fe-ver { margin-top: 6px; font-size: 12px; color: #999; }
.sheet-actions { margin-top: 12px; display: flex; gap: 8px; }
.sheet-title { text-align: center; font-size: 22px; letter-spacing: 4px; margin: 8px 0 16px; }
.sheet-head { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.sheet-head td { border: 1px solid #333; padding: 6px 10px; font-size: 14px; }
.sheet-head .lbl { width: 90px; background: #f5f5f5; font-weight: 600; text-align: center; }
.sign-grid { width: 100%; border-collapse: collapse; }
.sign-grid th, .sign-grid td { border: 1px solid #333; padding: 8px 10px; font-size: 14px; text-align: center; height: 34px; }
.sign-grid th { background: #f5f5f5; }
.sign-cell { height: 34px; }
.sign-foot { border: none !important; text-align: left; font-size: 13px; padding: 8px 2px !important; height: auto !important; }
.foot-cell { border: none !important; text-align: center; font-size: 12px; color: #333; letter-spacing: 1px; padding-top: 10px !important; height: auto !important; }

.print-root { display: none; }

@media print {
  .no-print { display: none !important; }
  @page { size: A4; margin: 14mm 12mm 26mm 12mm; }
  body > *:not(.print-root) { display: none !important; }
  /* 关键：页面可能同时挂着多张打印副本（组内/科内签到表、实习讲课签到表），
     只显示当前点「打印」的那一张；未设标记时不影响其它打印组件 */
  body[data-print-target] > .print-root { display: none !important; }
  body[data-print-target="sm"] > .print-root.pr-sm,
  body[data-print-target="ks"] > .print-root.pr-ks { display: block !important; }
  .print-root {
    position: static !important;
    width: 100% !important;
    visibility: visible !important;
  }
}
</style>
