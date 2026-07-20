<template>
  <div class="page">
    <div class="page-header">
      <h2 class="title">试剂目录</h2>
      <p class="sub">试剂、校准品、质控品、耗材一览表。支持搜索、筛选、Excel导入。</p>
    </div>

    <div class="toolbar">
      <el-input v-model="q" placeholder="搜索名称/品牌/编码..." clearable style="width:280px" @keyup.enter="refresh" @clear="refresh">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filterType" placeholder="全部类型" clearable style="width:130px" @change="refresh">
        <el-option v-for="t in types" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button :icon="Refresh" @click="refresh">刷新</el-button>
      <el-button type="primary" :icon="Plus" @click="onAdd" v-if="canWrite">新增</el-button>
      <el-button :icon="Upload" @click="onImport" v-if="canWrite">导入Excel</el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe height="calc(100vh - 340px)" empty-text="暂无数据">
      <el-table-column type="index" width="50" label="#" />
      <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="category" label="类别" width="90" />
      <el-table-column prop="brand" label="品牌" width="130" />
      <el-table-column prop="spec" label="规格" width="160" show-overflow-tooltip />
      <el-table-column prop="material_code" label="材料编码" width="130" />
      <el-table-column prop="unit" label="单位" width="70" />
      <el-table-column prop="min_stock" label="最低库存" width="90" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right" v-if="canWrite">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
      @current-change="refresh" @size-change="page=1; refresh()" />

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑试剂' : '新增试剂'" width="600px">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="类型"><el-select v-model="form.type" style="width:100%">
            <el-option v-for="t in types" :key="t" :label="t" :value="t" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类别"><el-select v-model="form.category" style="width:100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="form.brand" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="材料编码"><el-input v-model="form.material_code" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="规格"><el-input v-model="form.spec" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最低库存"><el-input-number v-model="form.min_stock" :min="0" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="生产厂家"><el-input v-model="form.manufacturer" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入 Excel 弹窗 -->
    <el-dialog v-model="importVisible" title="导入试剂目录" width="450px">
      <p style="color:#909399;margin-bottom:12px">上传 Excel 文件，第1行为表头，需包含「名称/试剂名称」列。支持列：类型、品牌、规格、材料编码、单位等。</p>
      <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".xls,.xlsx"
        :on-change="onFileChange" :file-list="[]">
        <el-button type="primary">选择文件</el-button>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible=false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="onUpload">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Upload } from '@element-plus/icons-vue'
import { listReagentItems, createReagentItem, updateReagentItem, deleteReagentItem, importReagentFromExcel } from '../../api/reagent'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('reagents'))
const types = ['试剂', '校准品', '质控品', '耗材']
const categories = ['生化', '免疫', '凝血', '血气', '尿液', '其他']

const items = ref([]), total = ref(0), page = ref(1), pageSize = ref(50), loading = ref(false)
const q = ref(''), filterType = ref('')
const dialogVisible = ref(false), editingId = ref(null), submitting = ref(false)
const importVisible = ref(false), uploading = ref(false)
const uploadFile = ref(null)

const emptyForm = () => ({
  name: '', type: '试剂', category: '', brand: '', spec: '', material_code: '',
  unit: '', manufacturer: '', supplier: '', min_stock: 0, remark: '', is_active: true,
})
const form = reactive(emptyForm())

async function refresh() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (q.value.trim()) params.q = q.value.trim()
    if (filterType.value) params.type = filterType.value
    const r = await listReagentItems(params)
    items.value = r.items; total.value = r.total
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e.message))
  } finally { loading.value = false }
}

function onAdd() {
  Object.assign(form, emptyForm()); editingId.value = null; dialogVisible.value = true
}
function onEdit(row) {
  Object.assign(form, { ...row }); editingId.value = row.id; dialogVisible.value = true
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await deleteReagentItem(row.id); ElMessage.success('已删除'); refresh()
}
async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) { await updateReagentItem(editingId.value, form) }
    else { await createReagentItem(form) }
    ElMessage.success('已保存'); dialogVisible.value = false; refresh()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally { submitting.value = false }
}

function onImport() { uploadFile.value = null; importVisible.value = true }
function onFileChange(file) { uploadFile.value = file.raw }
async function onUpload() {
  if (!uploadFile.value) { ElMessage.warning('请选择文件'); return }
  uploading.value = true
  try {
    const fd = new FormData(); fd.append('file', uploadFile.value)
    const r = await importReagentFromExcel(fd)
    ElMessage.success(`导入完成：新增 ${r.imported} 条，跳过 ${r.skipped} 条`)
    importVisible.value = false; refresh()
  } catch (e) {
    ElMessage.error('导入失败：' + (e?.response?.data?.detail || e.message))
  } finally { uploading.value = false }
}

onMounted(refresh)
</script>

<style scoped>
.page { padding: 16px 20px 0; display: flex; flex-direction: column; height: 100%; }
.page-header { margin-bottom: 8px; }
.title { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0; color: #64748b; font-size: 13px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin: 8px 0 12px; flex-wrap: wrap; }
.pager { margin: 10px 0 16px; display: flex; justify-content: flex-end; }
</style>
