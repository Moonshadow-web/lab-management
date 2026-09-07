<template>
  <div class="pre-job-auth">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索申请人"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
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
          <el-select v-model="positions" multiple style="width:100%" placeholder="按 GL-070 选择岗位">
            <el-option v-for="p in META" :key="p.name" :label="p.name" :value="p.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="考核仪器（多选）">
          <el-select v-model="instrumentCodes" multiple style="width:100%" placeholder="随岗位级联，可多选">
            <el-option v-for="i in instrumentOptions" :key="i.code" :label="i.name + '（' + i.code.replace('MHZYY-JYK-', '') + '）'" :value="i.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="授权权限（多选）">
          <el-select v-model="permissions" multiple style="width:100%" placeholder="授权上岗的岗位，可多选">
            <el-option v-for="p in META" :key="p.name" :label="p.name" :value="p.name" />
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
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import { printHtml } from '../../../utils/printHtml'
import { GL070_POSITIONS } from './gl070Meta'
import { listPreJobAuth, createPreJobAuth, updatePreJobAuth, deletePreJobAuth } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const META = GL070_POSITIONS
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
const form = ref(blank())
function blank() {
  return {
    id: null, name: '', apply_date: '', positions_json: [], instruments_json: [], permissions_json: [], items_json: [],
    theory_eval: '', operation_eval: '', group_leader_opinion: '', director_opinion: '', conclusion: '待审核', auth_date: '', status: '进行中', remark: '',
  }
}

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

// 岗位变化 → 清掉不在候选内的仪器，并同步逐项考核行
watch(positions, () => {
  const codes = new Set(instrumentOptions.value.map((i) => i.code))
  instrumentCodes.value = instrumentCodes.value.filter((c) => codes.has(c))
})
watch(instrumentCodes, () => {
  const map = new Map(GL070_META_ALL.value.map((i) => [i.code, i]))
  form.value.items_json = instrumentCodes.value.map((c) => {
    const old = (form.value.items_json || []).find((r) => r.code === c)
    const inst = map.get(c) || {}
    return { instrument: inst.name || '', code: c, items: old ? old.items : '', result: old ? old.result : '合格' }
  })
})
const GL070_META_ALL = computed(() => META.flatMap((p) => p.instruments.map((i) => ({ ...i, position: p.name }))))

function openForm(row) {
  if (row) {
    form.value = { ...blank(), ...row }
    positions.value = [...(row.positions_json || [])]
    instrumentCodes.value = (row.instruments_json || []).map((i) => i.code)
    permissions.value = [...(row.permissions_json || [])]
  } else {
    form.value = blank(); positions.value = []; instrumentCodes.value = []; permissions.value = []
  }
  visible.value = true
}
async function save() {
  try {
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
