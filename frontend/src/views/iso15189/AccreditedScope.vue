<template>
  <div>
    <div class="toolbar">
      <div class="hint">
        展示本室 CNAS 认可能力范围（参考《生免组申请认可的能力范围》）。下方直接显示 Excel 原始文本，包括多仪器、仪器编号、注册证号、试剂注册证号等。
      </div>
      <div class="ops">
        <el-input
          v-model="keyword"
          placeholder="搜索项目 / 方法 / 设备 / 试剂 / 校准品"
          clearable
          style="width: 280px"
        />
        <el-button v-if="auth.canManageIso15189" type="primary" @click="onAdd">新增项目</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <template v-if="groups.length === 0">
        <el-empty description="暂无数据，请先由管理员导入 Excel" />
      </template>
      <div v-for="g in groups" :key="g.key" class="group-block">
        <div class="group-title">
          <span class="l1">{{ g.l1 || '未分类' }}</span>
          <span v-if="g.l2" class="l2"> / {{ g.l2 }}</span>
          <span class="count">（{{ g.rows.length }} 项）</span>
        </div>
        <el-table :data="g.rows" border size="small" stripe style="width: 100%">
          <el-table-column prop="seq" label="序号" width="60" />
          <el-table-column prop="item_name" label="检验（检查）项目" min-width="150" show-overflow-tooltip />
          <el-table-column prop="sample_type" label="样品类型" width="90" />
          <el-table-column prop="method_name" label="方法" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="pre-line">{{ row.method_name || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="instrument_name" label="设备" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="pre-line">{{ row.instrument_name || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="reagent_name" label="试剂" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="pre-line">{{ row.reagent_name || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="calibrator" label="校准品" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="pre-line">{{ row.calibrator || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="perf_correctness" label="正确度" width="140" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.perf_correctness || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="perf_precision" label="精密度" width="140" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.perf_precision || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="perf_linearity" label="线性" width="110" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.perf_linearity || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="perf_reportable" label="可报告范围" width="130" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.perf_reportable || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="perf_other" label="其他" width="110" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.perf_other || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.description || '—' }}</span></template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip>
            <template #default="{ row }"><span class="pre-line">{{ row.remark || '—' }}</span></template>
          </el-table-column>
          <el-table-column v-if="auth.canManageIso15189" label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="onEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 编辑 / 新增 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑能力范围项目' : '新增能力范围项目'"
      width="860px"
      destroy-on-close
    >
      <el-form :model="form" label-width="110px" v-loading="optLoading">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="一级分类">
              <el-input v-model="form.category_l1" placeholder="如 A 检验医学" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="二级分类">
              <el-input v-model="form.category_l2" placeholder="如 AA 临床血液学" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="序号">
              <el-input v-model="form.seq" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目">
              <el-input v-model="form.item_name" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="样品类型">
              <el-input v-model="form.sample_type" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">系统关联（方法 / 设备 / 试剂）</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="方法">
              <el-select
                v-model="form.method_name"
                filterable allow-create default-first-option
                placeholder="选择或输入方法"
                style="width: 100%"
                @change="onMethodChange"
              >
                <el-option v-for="m in methodOptions" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="设备">
              <el-select
                v-model="form.instrument_name"
                filterable allow-create default-first-option
                placeholder="关联系统仪器"
                style="width: 100%"
                @change="onInstrumentChange"
              >
                <el-option v-for="i in instrumentOptions" :key="i.id" :label="i.name" :value="i.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="试剂">
              <el-select
                v-model="form.reagent_name"
                filterable allow-create default-first-option
                placeholder="关联系统试剂"
                style="width: 100%"
                @change="onReagentChange"
              >
                <el-option v-for="r in reagentOptions" :key="r.id" :label="r.name" :value="r.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="校准品">
              <el-input v-model="form.calibrator" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">分析性能</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="正确度"><el-input v-model="form.perf_correctness" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="精密度"><el-input v-model="form.perf_precision" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="线性"><el-input v-model="form.perf_linearity" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="可报告范围"><el-input v-model="form.perf_reportable" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="其他"><el-input v-model="form.perf_other" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">说明 / 备注</el-divider>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listScopes, createScope, updateScope, deleteScope } from '../../api/accreditedScope'
import { listInstruments } from '../../api/instruments'
import { listAllReagentItems } from '../../api/reagent'
import { listTestItems } from '../../api/testItems'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const loading = ref(false)
const optLoading = ref(false)
const keyword = ref('')
const items = ref([])

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)

const instrumentOptions = ref([])
const reagentOptions = ref([])
const methodOptions = ref([])
const instrumentMap = ref({}) // name -> id
const reagentMap = ref({})    // name -> id

const emptyForm = () => ({
  category_l1: '', category_l2: '', seq: '', item_name: '', sample_type: '',
  method_name: '', method_id: null,
  instrument_name: '', instrument_id: null,
  reagent_name: '', reagent_id: null,
  calibrator: '', description: '', remark: '',
  perf_correctness: '', perf_precision: '', perf_linearity: '',
  perf_reportable: '', perf_other: '',
})
const form = reactive(emptyForm())

const filteredItems = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return items.value
  return items.value.filter((it) =>
    [it.item_name, it.sample_type, it.method_name, it.instrument_name, it.reagent_name, it.calibrator]
      .filter(Boolean).some((v) => String(v).toLowerCase().includes(k))
  )
})

const groups = computed(() => {
  const map = new Map()
  for (const it of filteredItems.value) {
    const l1 = it.category_l1 || ''
    const l2 = it.category_l2 || ''
    const key = `${l1}||${l2}`
    if (!map.has(key)) map.set(key, { key, l1, l2, rows: [] })
    map.get(key).rows.push(it)
  }
  return Array.from(map.values())
})

async function loadOptions() {
  optLoading.value = true
  try {
    const [inst, reags, tis] = await Promise.all([
      listInstruments({ page_size: 1000 }),
      listAllReagentItems(),
      listTestItems({ page_size: 2000 }),
    ])
    const instList = inst.items || []
    instrumentOptions.value = instList
    instrumentMap.value = {}
    instList.forEach((i) => { if (i.name) instrumentMap.value[i.name] = i.id })

    reagentOptions.value = reags || []
    reagentMap.value = {}
    ;(reags || []).forEach((r) => { if (r.name) reagentMap.value[r.name] = r.id })

    const ms = new Set()
    ;(tis.items || []).forEach((t) => { if (t.method) ms.add(t.method) })
    methodOptions.value = Array.from(ms).sort()
  } catch (e) {
    // 选项加载失败不阻断主表展示
  } finally {
    optLoading.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const r = await listScopes({ page_size: 2000 })
    items.value = r.items || []
  } catch (e) {
    ElMessage.error('加载认可能力范围失败')
  } finally {
    loading.value = false
  }
}

function onMethodChange(val) {
  // 方法非独立实体，仅保留文本；不设置 method_id
  form.method_name = val || ''
  form.method_id = null
}
function onInstrumentChange(val) {
  form.instrument_name = val || ''
  form.instrument_id = instrumentMap.value[val] != null ? instrumentMap.value[val] : null
}
function onReagentChange(val) {
  form.reagent_name = val || ''
  form.reagent_id = reagentMap.value[val] != null ? reagentMap.value[val] : null
}

function onAdd() {
  Object.assign(form, emptyForm())
  editingId.value = null
  dialogVisible.value = true
}
function onEdit(row) {
  Object.assign(form, emptyForm(), JSON.parse(JSON.stringify(row)))
  editingId.value = row.id
  dialogVisible.value = true
}
async function onSubmit() {
  if (!form.item_name) {
    ElMessage.warning('请填写检验（检查）项目')
    return
  }
  submitting.value = true
  try {
    const payload = { ...form }
    if (editingId.value) await updateScope(editingId.value, payload)
    else await createScope(payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.item_name}」？`, '提示', { type: 'warning' })
  await deleteScope(row.id)
  ElMessage.success('已删除')
  await loadData()
}

onMounted(() => {
  loadData()
  loadOptions()
})
</script>

<style scoped>
.toolbar {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 12px; margin-bottom: 12px; flex-wrap: wrap;
}
.hint { font-size: 13px; color: #606266; line-height: 1.6; max-width: 720px; }
.hint .warn { color: #e6a23c; }
.ops { display: flex; gap: 8px; align-items: center; }
.group-block { margin-bottom: 18px; }
.group-title {
  font-weight: 600; font-size: 15px; color: #303133;
  padding: 6px 0; border-left: 4px solid #409eff; padding-left: 10px; margin-bottom: 6px;
  background: #f5f7fa;
}
.group-title .l1 { color: #303133; }
.group-title .l2 { color: #606266; }
.group-title .count { color: #909399; font-weight: 400; font-size: 13px; }
.pre-line {
  white-space: pre-line;
  line-height: 1.5;
  display: inline-block;
}
</style>
