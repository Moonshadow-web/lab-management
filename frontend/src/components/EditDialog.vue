<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="680px"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item
        v-for="f in fields"
        :key="f.prop"
        :label="f.label"
        :prop="f.prop"
      >
        <el-select
          v-if="f.type === 'select'"
          v-model="form[f.prop]"
          :placeholder="f.placeholder || '请选择'"
          style="width: 100%"
        >
          <el-option
            v-for="opt in f.options"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-input
          v-else-if="f.type === 'textarea'"
          v-model="form[f.prop]"
          type="textarea"
          :rows="3"
          :placeholder="f.placeholder"
        />
        <el-switch v-else-if="f.type === 'switch'" v-model="form[f.prop]" />
        <el-date-picker
          v-else-if="f.type === 'date'"
          v-model="form[f.prop]"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
        <el-input v-else v-model="form[f.prop]" :placeholder="f.placeholder" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '编辑' },
  form: { type: Object, required: true },
  fields: { type: Array, required: true },
  rules: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const formRef = ref(null)

function onOpen() {
  formRef.value?.clearValidate?.()
}

async function onSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    emit('submit')
  } catch (e) {
    // 校验失败，不提交
  }
}
</script>
