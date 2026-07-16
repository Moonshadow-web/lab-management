<template>
  <div class="crud-table">
    <div class="crud-toolbar">
      <el-input
        v-model="q"
        :placeholder="searchPlaceholder || '搜索...'"
        clearable
        style="width: 280px"
        @keyup.enter="refresh"
        @clear="refresh"
      >
        <template #append>
          <el-button :icon="Search" @click="refresh" />
        </template>
      </el-input>
      <div class="spacer" />
      <slot name="toolbar-extra" />
      <el-button v-if="showAdd && canWrite" type="primary" :icon="Plus" @click="$emit('add')">新增</el-button>
    </div>

    <div class="table-wrap">
      <el-table v-loading="loading" :data="rows" border stripe height="100%">
        <el-table-column type="index" label="#" width="50" align="center" />
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth || 120"
          :show-overflow-tooltip="col.tooltip !== false"
        >
          <template v-if="col.formatter" #default="{ row }">
            <span v-html="col.formatter(row)"></span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="actionWidth" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canWrite" link type="primary" :icon="Edit" @click="$emit('edit', row)">编辑</el-button>
            <el-button v-if="canWrite" link type="danger" :icon="Delete" @click="$emit('delete', row)">删除</el-button>
            <slot name="row-extra" :row="row" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="crud-pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="refresh"
        @size-change="refresh"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  columns: { type: Array, required: true },
  fetch: { type: Function, required: true },
  searchPlaceholder: { type: String, default: '搜索...' },
  showAdd: { type: Boolean, default: true },
  canWrite: { type: Boolean, default: true },
  actionWidth: { type: [Number, String], default: 140 },
  extraParams: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['add', 'edit', 'delete'])

const q = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

async function refresh() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value, ...props.extraParams, q: q.value }
    const res = await props.fetch(params)
    rows.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
defineExpose({ refresh, q })
</script>

<style scoped>
.crud-table {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.crud-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.spacer {
  flex: 1;
}
.crud-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
@media (max-width: 768px) {
  .table-wrap {
    overflow-x: auto;
  }
  .table-wrap :deep(.el-table) {
    min-width: 760px;
  }
  .table-wrap :deep(.el-button.is-link),
  .table-wrap :deep(.el-button--text) {
    display: block;
    margin: 2px 0;
    padding: 4px 0;
    line-height: 1.4;
    text-align: center;
  }
}
</style>
