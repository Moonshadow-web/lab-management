<template>
  <div class="sign-in-sheet">
    <div class="no-print toolbar">
      <el-alert type="info" :closable="false" title="打印空白签到表 → 现场签名 → 扫描后上传到「签到扫描件」页签留存">
        打印后手工签名，再将扫描件上传到上方"课件 / 通知 / 考题 / 效果评价 / 签到 存档"的「签到扫描件」页签，即完成 BG-SM-PX-006 签到表归档。
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
      <h2 class="sheet-title">生化免疫组培训签到表</h2>
      <table class="sheet-head">
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
            <th>姓名</th><th>职称</th><th>签到</th>
            <th>姓名</th><th>职称</th><th>签到</th>
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
      </table>
    </div>

    <!-- 打印专用：Teleport 到 body，仅打印时显示，规避 el-dialog fixed 浮层打印空白 -->
    <Teleport to="body">
      <div class="print-root sheet" v-if="rows.length">
        <h2 class="sheet-title">生化免疫组培训签到表</h2>
        <table class="sheet-head">
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
              <th>姓名</th><th>职称</th><th>签到</th>
              <th>姓名</th><th>职称</th><th>签到</th>
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
        </table>
        <div class="sheet-foot">表格编号：BG-SM-PX-006　　检验科生化免疫组　　生效日期：2026.9.1</div>
      </div>
    </Teleport>

    <div class="no-print">
      <el-divider content-position="left">编辑签到名单（打印前可调）</el-divider>
      <el-table :data="uniqueRows" border size="small">
        <el-table-column label="姓名" width="160">
          <template #default="{ row, $index }">
            <el-input v-model="row.name" placeholder="姓名" @input="persistHeader()" />
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
})

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
// 注意：空名单行必须保留——否则「加一行」新增的空行会被过滤掉，表现为点了没反应
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
  // 两两配对：奇数长度时循环本身已把最后一人放到 left（right=null），切勿再重复 push
  for (let i = 0; i < uniqueRows.value.length; i += 2) {
    out.push({ left: uniqueRows.value[i], right: uniqueRows.value[i + 1] || null })
  }
  // 保证至少 30 行（与原表行数相当）
  while (out.length < 30) out.push({ left: null, right: null })
  return out
})

function addRow() { rows.value.push({ name: '', title: '' }) }
function removeRow(r) { rows.value = rows.value.filter((x) => x !== r) }
function clearRows() { rows.value = [] }

function persistHeader() {
  // 名单变化不影响 header，但保留钩子便于扩展
}

async function doPrint() {
  // 保存当前名单到 session 的 sign_in_header（通过父组件），再打印
  emitSaveHeader()
  await new Promise((r) => setTimeout(r, 100))
  window.print()
}

const emit = defineEmits(['save-header'])
function emitSaveHeader() {
  // 持久化前再次去重，确保存库名单不含重复姓名
  emit('save-header', { names: dedupeNames(uniqueRows.value.map((r) => ({ name: r.name, title: r.title }))) })
}

// 排除“培训老师”本人，并去重（避免编辑记录里出现两个金子铮）
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
  } else {
    // 预填生免室人员名单（去重 + 排除培训老师）
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
.sheet-foot { text-align: center; font-size: 12px; color: #333; margin-top: 14px; letter-spacing: 1px; }

/* 打印专用副本：屏显隐藏，仅打印时通过 Teleport 到 body 显示 */
.print-root { display: none; }

@media print {
  .no-print { display: none !important; }
  @page { size: A4; margin: 16mm; }
  /* print-root 已 Teleport 到 body，直接隐藏其它 body 子元素，避免 el-dialog fixed 浮层打印空白 */
  body > *:not(.print-root) { display: none !important; }
  .print-root {
    display: block !important;
    position: static !important;
    width: 100% !important;
    visibility: visible !important;
  }
}
</style>
