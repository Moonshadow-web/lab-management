<template>
  <el-dialog :model-value="visible" :title="plan ? '编辑比对计划' : '新建比对计划'" width="640px"
    @update:model-value="(v) => !v && $emit('close')">
    <el-form :model="form" label-width="100px">
      <el-form-item label="比对分组" required>
        <el-select v-model="form.group_id" filterable style="width:100%" @change="onGroupChange">
          <el-option v-for="g in groups" :key="g.id" :label="`${g.name}（${g.form_code}）`" :value="g.id" />
        </el-select>
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="10">
          <el-form-item label="年份" required>
            <el-input-number v-model="form.year" :min="2000" :max="2100" />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item label="比对周期">
            <el-radio-group v-model="form.half">
              <el-radio :value="1">上半年</el-radio>
              <el-radio :value="2">下半年</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="比对日期">
            <el-date-picker v-model="form.compared_at" type="date" value-format="YYYY-MM-DD"
              style="width:100%" placeholder="比对日期" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option label="草稿" value="draft" />
              <el-option label="已完成" value="done" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="!plan" label="范围">
        <el-checkbox v-model="form.only_uncompared">
          仅纳入本期未比对项目（同分组同半年补录：自动排除已做项，录入时只显示待做项目）
        </el-checkbox>
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="操作者">
            <UserSelect v-model="form.operator" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="审核者">
            <UserSelect v-model="form.reviewer" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="结果分析">
        <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="各仪器上述所有项目均比对合格。" />
      </el-form-item>
      <el-form-item label="结论">
        <el-select v-model="form.conclusion" clearable style="width:100%">
          <el-option label="可接受" value="可接受" />
          <el-option label="不可接受" value="不可接受" />
        </el-select>
      </el-form-item>
      <el-form-item label="处理方案">
        <el-input v-model="form.handle_plan" type="textarea" :rows="2" placeholder="如不合格的处理方案" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createPlan, updatePlan } from '../../api/comparison'
import UserSelect from '../../components/UserSelect.vue'

const props = defineProps({
  visible: Boolean,
  plan: { type: Object, default: null },
  groups: { type: Array, default: () => [] },
  defaultGroupId: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'saved'])
const form = reactive({
  group_id: null, year: new Date().getFullYear(), half: 1, compared_at: '', operator: '',
  reviewer: '', summary: '', conclusion: '', handle_plan: '', status: 'draft',
  only_uncompared: false,
  form_code: '', form_title: '',
})
const saving = ref(false)

function onGroupChange(gid) {
  const g = props.groups.find((x) => x.id === gid)
  if (g) {
    form.form_code = g.form_code
    form.form_title = g.form_title
  }
}
watch(() => props.visible, (v) => {
  if (!v) return
  if (props.plan) {
    Object.assign(form, {
      group_id: props.plan.group_id, year: props.plan.year, half: props.plan.half,
      compared_at: props.plan.compared_at, operator: props.plan.operator,
      reviewer: props.plan.reviewer, summary: props.plan.summary, conclusion: props.plan.conclusion,
      handle_plan: props.plan.handle_plan, status: props.plan.status || 'draft',
      only_uncompared: !!props.plan.only_uncompared,
      form_code: props.plan.form_code, form_title: props.plan.form_title,
    })
  } else {
    const gid = props.defaultGroupId || (props.groups[0] && props.groups[0].id)
    Object.assign(form, {
      group_id: gid, year: new Date().getFullYear(), half: 1, compared_at: '', operator: '',
      reviewer: '', summary: '', conclusion: '', handle_plan: '', status: 'draft',
      only_uncompared: false,
      form_code: '', form_title: '',
    })
    if (gid) onGroupChange(gid)
  }
})

async function onSave() {
  if (!form.group_id) return ElMessage.warning('请选择比对分组')
  if (!form.year) return ElMessage.warning('请填写年份')
  const payload = {
    group_id: form.group_id, year: form.year, half: form.half, compared_at: form.compared_at,
    operator: form.operator, reviewer: form.reviewer, summary: form.summary,
    conclusion: form.conclusion, handle_plan: form.handle_plan, status: form.status,
    only_uncompared: form.only_uncompared,
    form_code: form.form_code, form_title: form.form_title,
  }
  saving.value = true
  try {
    if (props.plan) await updatePlan(props.plan.id, payload)
    else await createPlan(payload)
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
