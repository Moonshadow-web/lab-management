<template>
  <div class="library-tabs">
    <span class="label">责任库：</span>
    <el-radio-group :model-value="library" @update:model-value="onChange" size="small">
      <el-radio-button v-for="lib in libs" :key="lib" :value="lib">{{ lib }}</el-radio-button>
    </el-radio-group>
    <span class="hint">（生化凝血 / 免疫 分开管理，两人各管一类）</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useReagentStore, LIBRARIES } from '../../store/reagent'

const reagentStore = useReagentStore()
const libs = LIBRARIES
const library = computed(() => reagentStore.library)

function onChange(val) {
  reagentStore.setLibrary(val)
  emit('change', val)
}
const emit = defineEmits(['change'])
</script>

<style scoped>
.library-tabs { display: flex; align-items: center; gap: 8px; margin: 4px 0 10px; flex-wrap: wrap; }
.library-tabs .label { font-size: 13px; color: #475569; font-weight: 600; }
.library-tabs .hint { font-size: 12px; color: #94a3b8; }
</style>
