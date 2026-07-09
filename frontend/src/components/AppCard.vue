<template>
  <el-card class="app-card" shadow="hover">
    <template v-if="title || $slots['header-extra']" #header>
      <div class="app-card-header">
        <span class="app-card-title">{{ title }}</span>
        <slot name="header-extra" />
      </div>
    </template>
    <slot />
  </el-card>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>

<style scoped>
.app-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.app-card-title {
  font-weight: 600;
}
</style>
