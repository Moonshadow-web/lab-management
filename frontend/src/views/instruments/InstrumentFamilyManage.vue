<template>
  <div class="page">
    <div class="toolbar">
      <div>
        <h2 class="page-title">仪器关联管理</h2>
        <p class="page-desc">维护「项目使用仪器（总型号）→ 仪器档案」的一对多对应关系，供项目查询页点击跳转仪器档案。</p>
      </div>
      <el-button type="primary" :icon="Plus" size="large" @click="onAdd">新增总型号</el-button>
    </div>

    <el-table v-loading="loading" :data="families" border stripe style="width:100%">
      <el-table-column prop="name" label="总型号（使用仪器）" min-width="220">
        <template #default="{ row }">
          <strong>{{ row.name }}</strong>
          <el-tag v-if="row.description" size="small" type="info" effect="plain" class="desc-tag">{{ row.description }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="关联仪器数" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="row.member_count ? 'success' : 'info'">{{ row.member_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="项目使用数" width="110" align="center" prop="used_count">
        <template #default="{ row }">
          <el-tag :type="row.used_count ? 'warning' : 'info'">{{ row.used_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="已关联仪器" min-width="320">
        <template #default="{ row }">
          <template v-if="row.members && row.members.length">
            <el-tag
              v-for="m in row.members"
              :key="m.id"
              size="small"
              effect="plain"
              class="mem-tag"
              :type="m.has_archive ? 'success' : 'info'"
            >{{ m.name }}（{{ m.model }}）<span v-if="!m.has_archive" class="no-arch">· 未建档</span><span v-if="m.status && m.status !== '在用'" class="st-tag">· {{ m.status }}</span></el-tag>
          </template>
          <span v-else class="muted">— 未关联 —</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" :icon="Edit" @click="onEdit(row)">编辑</el-button>
          <el-button text type="danger" :icon="Delete" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑总型号关联' : '新增总型号'" width="640px">
      <el-form label-width="92px">
        <el-form-item label="总型号" required>
          <el-input v-model="form.name" placeholder="如：罗氏 Cobas6000 / AU生化仪" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" placeholder="可选，如：含 e601/e602/e411 三台" />
        </el-form-item>
        <el-form-item label="关联仪器">
          <el-select
            v-model="form.instrument_ids"
            multiple
            filterable
            clearable
            style="width:100%"
            placeholder="选择对应的具体仪器（可搜索型号/名称）"
          >
            <el-option
              v-for="inst in allInstruments"
              :key="inst.id"
              :value="inst.id"
              :label="`${inst.name}（${inst.model}）${inst.has_archive ? '' : ' · 未建档'}`"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import {
  listInstrumentFamilies,
  createInstrumentFamily,
  updateInstrumentFamily,
  deleteInstrumentFamily,
  setFamilyMembers,
  getInstrumentFamily,
  listInstruments,
  getArchivesStatus,
} from '../../api/instruments'

const families = ref([])
const allInstruments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)

const form = reactive({ name: '', description: '', instrument_ids: [] })

onMounted(() => {
  loadInstruments()
  fetchFamilies()
})

async function loadInstruments() {
  try {
    const res = await listInstruments({ page_size: 1000 })
    const items = res.items || []
    let archMap = {}
    try {
      const st = await getArchivesStatus()
      ;(st || []).forEach((a) => { archMap[a.instrument_id] = a.has_archive })
    } catch (e) {}
    // 停用仪器不纳入关联候选（不显示、不可跳转）；空字符串 status 会被后端当成 status=='' 导致全空，故此处拉全量再过滤
    allInstruments.value = items
      .filter((i) => i.status !== '停用')
      .map((i) => ({ ...i, has_archive: !!archMap[i.id] }))
  } catch (e) {
    allInstruments.value = []
  }
}

async function fetchFamilies() {
  loading.value = true
  try {
    families.value = await listInstrumentFamilies()
  } catch (e) {
    ElMessage.error('加载关联失败')
  } finally {
    loading.value = false
  }
}

function onAdd() {
  editingId.value = null
  Object.assign(form, { name: '', description: '', instrument_ids: [] })
  dialogVisible.value = true
}

async function onEdit(row) {
  editingId.value = row.id
  try {
    const detail = await getInstrumentFamily(row.id)
    Object.assign(form, {
      name: detail.name,
      description: detail.description || '',
      instrument_ids: (detail.instrument_ids || []).filter((id) => {
        const inst = allInstruments.value.find((i) => i.id === id)
        return inst && inst.status !== '停用'
      }),
    })
    dialogVisible.value = true
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

async function onSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写总型号')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateInstrumentFamily(editingId.value, { description: form.description })
      await setFamilyMembers(editingId.value, form.instrument_ids)
    } else {
      const created = await createInstrumentFamily({ name: form.name.trim(), description: form.description })
      await setFamilyMembers(created.id, form.instrument_ids)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    fetchFamilies()
  } catch (e) {
    const detail = e?.response?.data?.detail
    ElMessage.error('保存失败：' + (typeof detail === 'string' ? detail : (e?.message || '未知错误')))
  } finally {
    saving.value = false
  }
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除总型号「${row.name}」及其关联？`, '提示', { type: 'warning' })
  await deleteInstrumentFamily(row.id)
  ElMessage.success('已删除')
  fetchFamilies()
}
</script>

<style scoped>
.page {
  padding: 16px 20px 24px;
  background: #f5f7fa;
  min-height: 100%;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}
.page-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: #1a365d;
}
.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
  max-width: 680px;
}
.desc-tag {
  margin-left: 8px;
}
.mem-tag {
  margin: 0 6px 6px 0;
}
.no-arch {
  color: #c0c4cc;
  font-size: 12px;
}
.muted {
  color: #c0c4cc;
}
</style>
