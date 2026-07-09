<template>
  <el-upload
    drag
    :auto-upload="false"
    :show-file-list="true"
    :limit="1"
    :on-change="onChange"
    :on-remove="onRemove"
    :accept="accept"
  >
    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
    <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
    <template #tip>
      <div class="el-upload__tip">{{ tip }}</div>
    </template>
  </el-upload>
</template>

<script setup>
import { UploadFilled } from '@element-plus/icons-vue'

defineProps({
  accept: { type: String, default: '' },
  tip: { type: String, default: '' },
})

const emit = defineEmits(['change'])

function onChange(uploadFile) {
  emit('change', uploadFile.raw || null)
}
function onRemove() {
  emit('change', null)
}
</script>
