<template>
  <div class="library-tabs">
    <span class="label">责任库：</span>
    <el-radio-group v-model="selected" size="small" @change="onRadioChange">
      <el-radio-button v-for="lib in libs" :key="lib" :value="lib">{{ lib }}</el-radio-button>
    </el-radio-group>
    <span class="hint">（生化凝血 / 免疫 分开管理，两人各管一类）</span>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useReagentStore, LIBRARIES } from '../../store/reagent'

const reagentStore = useReagentStore()
const libs = LIBRARIES
const selected = ref(reagentStore.library)

// 外部切换（如其他页面修改了 store）时同步回来
watch(() => reagentStore.library, (val) => {
  if (val !== selected.value) selected.value = val
})

function onRadioChange(val) {
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
