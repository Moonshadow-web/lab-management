<template>
  <el-dialog :model-value="visible" :title="group ? '编辑比对分组' : '新建比对分组'" width="880px"
    @update:model-value="(v) => !v && $emit('close')" @open="onOpen">
    <el-form :model="form" label-width="110px">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="分组名称" required>
            <el-input v-model="form.name" placeholder="如：生化分析仪" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="类型">
            <el-radio-group v-model="form.category">
              <el-radio value="定量">定量</el-radio>
              <el-radio value="定性">定性</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="表格编号" required>
            <el-input v-model="form.form_code" placeholder="BG-SM-CZ-025" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="水平数">
            <el-input-number v-model="form.levels" :min="1" :max="10" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="表单标题">
        <el-input v-model="form.form_title" placeholder="定量室内比对结果记录分析表（生化分析仪）" />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="14">
          <el-form-item label="组内仪器" required>
            <el-select v-model="form.instrument_ids" multiple filterable placeholder="选择2台及以上仪器（显示型号）"
              style="width:100%">
              <el-option v-for="i in instruments" :key="i.id" :label="i.name" :value="i.id">
                <span>{{ i.name }}</span>
                <el-tag v-if="i.status && i.status !== '在用'" type="info" size="small"
                  effect="plain" style="margin-left:6px">{{ i.status }}</el-tag>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="10">
          <el-form-item label="参照仪器">
            <el-select v-model="form.reference_instrument_id" filterable placeholder="标准/参照"
              style="width:100%">
              <el-option v-for="i in selectedInstruments" :key="i.id" :label="i.name" :value="i.id" />
              <el-option v-if="!form.instrument_ids.includes(form.reference_instrument_id) && form.reference_instrument_id"
                :label="refName" :value="form.reference_instrument_id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="样本描述">
        <el-input v-model="form.sample_desc" placeholder="5个不同浓度水平的室间质评样本" />
      </el-form-item>

      <el-form-item label="比对项目">
        <div style="width:100%">
          <div class="items-tip">
            <el-button size="small" type="primary" plain :loading="resolving"
              :disabled="form.instrument_ids.length < 2" @click="onResolve">
              按仪器档案生成共有项目
            </el-button>
            <span class="hint">
              依据仪器档案「项目↔仪器」关联，自动列出该仪器组共有项目及每项适用仪器；
              「适用仪器」留空=组内全部，录入/报告时对不适用的仪器自动遮蔽（显示 /）。
            </span>
          </div>
          <el-table :data="form.items" size="small" border style="margin-top:8px">
            <el-table-column label="项目代码" min-width="110">
              <template #default="{ row }"><el-input v-model="row.name" size="small" /></template>
            </el-table-column>
            <el-table-column label="中文名" min-width="120">
              <template #default="{ row }"><el-input v-model="row.label" size="small" /></template>
            </el-table-column>
            <el-table-column label="允许TE" width="100">
              <template #default="{ row }"><el-input v-model="row.te" size="small" placeholder="2 或 0.02" /></template>
            </el-table-column>
            <el-table-column label="偏倚方式" width="106">
              <template #default="{ row }">
                <el-select v-model="row.mode" size="small">
                  <el-option label="相对%" value="relative" />
                  <el-option label="绝对" value="absolute" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="适用仪器（遮蔽）" min-width="200">
              <template #default="{ row }">
                <el-select v-model="row.instrument_ids" multiple collapse-tags collapse-tags-tooltip
                  size="small" placeholder="留空=全部" style="width:100%">
                  <el-option v-for="i in selectedInstruments" :key="i.id" :label="i.name" :value="i.id" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="" width="46">
              <template #default="{ $index }">
                <el-button type="danger" link size="small" @click="form.items.splice($index, 1)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" @click="form.items.push({ name: '', label: '', te: '0', mode: 'relative', instrument_ids: [] })"
            style="margin-top:6px">+ 新增项目</el-button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createGroup, updateGroup, resolveItems } from '../../api/comparison'

const props = defineProps({
  visible: Boolean,
  group: { type: Object, default: null },
  instruments: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const form = reactive({
  name: '', category: '定量', form_code: '', form_title: '', instrument_ids: [],
  reference_instrument_id: null, levels: 5, sample_desc: '', items: [],
})
const saving = ref(false)
const resolving = ref(false)

const selectedInstruments = computed(() =>
  props.instruments.filter((i) => form.instrument_ids.includes(i.id)))
const refName = computed(() => {
  const i = props.instruments.find((x) => x.id === form.reference_instrument_id)
  return i ? i.name : '参照仪器'
})

function normItem(i) {
  return {
    name: i.name || '', label: i.label || '', te: i.te != null ? String(i.te) : '0',
    mode: i.mode || 'relative', instrument_ids: Array.isArray(i.instrument_ids) ? [...i.instrument_ids] : [],
  }
}

function onOpen() {
  if (props.group) {
    Object.assign(form, {
      name: props.group.name, category: props.group.category, form_code: props.group.form_code,
      form_title: props.group.form_title, instrument_ids: [...props.group.instrument_ids],
      reference_instrument_id: props.group.reference_instrument_id || null,
      levels: props.group.levels, sample_desc: props.group.sample_desc,
      items: (props.group.items || []).map(normItem),
    })
  } else {
    Object.assign(form, {
      name: '', category: '定量', form_code: '', form_title: '', instrument_ids: [],
      reference_instrument_id: null, levels: 5, sample_desc: '', items: [],
    })
  }
}
watch(() => props.visible, (v) => v && onOpen())

async function onResolve() {
  if (form.instrument_ids.length < 2) return ElMessage.warning('请先选择2台及以上组内仪器')
  if (form.items.length) {
    try {
      await ElMessageBox.confirm('将根据仪器档案重新生成项目清单，覆盖当前已填项目。是否继续？',
        '生成共有项目', { type: 'warning' })
    } catch { return }
  }
  resolving.value = true
  try {
    const r = await resolveItems({
      instrument_ids: form.instrument_ids, category: form.category, min_count: 2,
    })
    const items = (r.items || []).map(normItem)
    if (!items.length) {
      ElMessage.warning('未从仪器档案解析到该仪器组的共有项目，请检查仪器与项目关联或手动添加')
    } else {
      form.items = items
      ElMessage.success(`已生成 ${items.length} 个共有项目（含每项适用仪器）`)
    }
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    resolving.value = false
  }
}

async function onSave() {
  if (!form.name) return ElMessage.warning('请填写分组名称')
  if (!form.form_code) return ElMessage.warning('请填写表格编号')
  if (form.instrument_ids.length < 2) return ElMessage.warning('至少选择2台仪器')
  if (!form.items.length) return ElMessage.warning('请至少添加一个比对项目')
  const payload = {
    name: form.name, category: form.category, form_code: form.form_code, form_title: form.form_title,
    instrument_ids: form.instrument_ids, reference_instrument_id: form.reference_instrument_id || 0,
    levels: form.levels, sample_desc: form.sample_desc,
    items: form.items.filter((i) => i.name).map((i) => ({
      name: i.name, label: i.label || '', te: String(i.te), mode: i.mode,
      // 仅保留仍在组内的适用仪器；空=全部（遮蔽依据）
      instrument_ids: (i.instrument_ids || []).filter((x) => form.instrument_ids.includes(x)),
    })),
  }
  saving.value = true
  try {
    if (props.group) await updateGroup(props.group.id, payload)
    else await createGroup(payload)
    ElMessage.success('已保存')
    emit('saved')
    emit('close')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.items-tip { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.items-tip .hint { color: #909399; font-size: 12px; line-height: 1.4; }
</style>
