<template>
  <div class="child-table">
    <div class="ct-toolbar">
      <el-button v-if="canWrite" type="primary" :icon="Plus" @click="openForm()">新增</el-button>
    </div>
    <el-table :data="rows" border stripe size="small" v-loading="loading">
      <el-table-column type="index" label="#" width="46" align="center" />
      <el-table-column
        v-for="f in fields"
        :key="f.k"
        :prop="f.k"
        :label="f.l"
        min-width="120"
        show-overflow-tooltip
      />
      <el-table-column label="操作" width="140" align="center" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button link type="primary" :icon="Edit" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="model.id ? '编辑' : '新增'" width="520px" append-to-body>
      <el-form :model="model" label-width="110px">
        <el-form-item v-for="f in fields" :key="f.k" :label="f.l">
          <el-input v-model="model[f.k]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import {
  listPersonnelChild, createPersonnelChild, updatePersonnelChild, deletePersonnelChild,
} from '../../../api/education'

const props = defineProps({
  ownerId: { type: [Number, String], required: true },
  path: { type: String, required: true },
  fields: { type: Array, required: true },
  canWrite: { type: Boolean, default: true },
})
const emit = defineEmits(['changed'])

const rows = ref([])
const loading = ref(false)
const visible = ref(false)
const model = ref({})

function blankModel() {
  const m = { id: null, person_id: Number(props.ownerId) }
  for (const f of props.fields) m[f.k] = ''
  return m
}
function openForm(row) {
  model.value = row ? { ...row } : blankModel()
  visible.value = true
}
async function refresh() {
  loading.value = true
  try {
    const res = await listPersonnelChild(props.path, { person_id: props.ownerId, page: 1, page_size: 200 })
    rows.value = res.items || []
  } finally { loading.value = false }
}
async function save() {
  try {
    if (model.value.id) await updatePersonnelChild(props.path, model.value.id, model.value)
    else await createPersonnelChild(props.path, model.value)
    ElMessage.success('已保存')
    visible.value = false
    refresh()
    emit('changed')
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function remove(row) {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
    await deletePersonnelChild(props.path, row.id)
    ElMessage.success('已删除')
    refresh()
    emit('changed')
  } catch (e) {}
}

onMounted(refresh)
</script>

<style scoped>
.ct-toolbar { margin-bottom: 8px; }
</style>
