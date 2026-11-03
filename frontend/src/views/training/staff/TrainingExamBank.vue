<template>
  <div class="training-bank">
    <div class="tb-head">
      <span class="tb-tip">培训考核题库（按培训主题归档，可在「组内培训 → 扫码答题」中直接引用）</span>
      <div class="tb-actions">
        <el-select v-model="category" size="small" style="width:120px" @change="load">
          <el-option label="全部类别" value="" />
          <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>
        <el-input v-model="keyword" size="small" placeholder="搜索培训主题" clearable style="width:180px" @keyup.enter="load" @clear="load" />
        <el-button size="small" @click="load">搜索</el-button>
        <el-button type="primary" size="small" :disabled="!canWrite" @click="openForm()">新增培训题库</el-button>
      </div>
    </div>

    <el-table :data="list" border size="small" v-loading="loading">
      <el-table-column prop="topic" label="培训主题" min-width="240" show-overflow-tooltip />
      <el-table-column prop="category" label="类别" width="100" align="center" />
      <el-table-column label="题量" width="150" align="center">
        <template #default="{ row }">
          {{ row.count }} 题<span style="color:#909399;font-size:12px">（单 {{ row.single }} / 多 {{ row.multi }} / 判 {{ row.judge }}）</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.complete ? 'success' : 'warning'">{{ row.complete ? '题目完整' : '待补选项' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="source" label="来源" min-width="200" show-overflow-tooltip />
      <el-table-column label="更新" width="150" align="center">
        <template #default="{ row }">{{ (row.updated_at || '').replace('T', ' ').slice(0, 16) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openView(row)">查看</el-button>
          <el-button link type="primary" :disabled="!canWrite" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" :disabled="!canWrite" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty><div style="padding:20px;color:#909399">暂无培训题库</div></template>
    </el-table>

    <!-- 查看题目 -->
    <el-dialog v-model="viewVisible" :title="`${viewRow.topic || ''} · 题目`" width="820px" top="5vh">
      <el-alert v-if="viewRow.complete === false" type="warning" :closable="false" show-icon
        title="该题库来自历史答卷导出，仅有题干与参考答案，选项需补全后才能直接组卷。" style="margin-bottom:10px" />
      <div v-for="(q, i) in viewData.single || []" :key="'s' + i" class="qitem">
        <div><b>单选 {{ i + 1 }}.</b> {{ q.q }}</div>
        <div v-for="(o, oi) in q.options || []" :key="oi" class="opt">{{ o }}</div>
        <div class="ans">答案：<b>{{ q.answer }}</b></div>
      </div>
      <div v-for="(q, i) in viewData.multi || []" :key="'m' + i" class="qitem">
        <div><b>多选 {{ i + 1 }}.</b> {{ q.q }}</div>
        <div v-for="(o, oi) in q.options || []" :key="oi" class="opt">{{ o }}</div>
        <div class="ans">答案：<b>{{ q.answer }}</b></div>
      </div>
      <div v-for="(q, i) in viewData.judge || []" :key="'j' + i" class="qitem">
        <div><b>判断 {{ i + 1 }}.</b> {{ q.q }}</div>
        <div class="ans">答案：<b>{{ q.answer }}</b></div>
      </div>
    </el-dialog>

    <!-- 新增/编辑 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑培训题库' : '新增培训题库'" width="820px" top="5vh">
      <el-form label-width="90px">
        <el-row :gutter="12">
          <el-col :span="14"><el-form-item label="培训主题"><el-input v-model="form.topic" placeholder="如 D-二聚体（ADD）专项培训" /></el-form-item></el-col>
          <el-col :span="10"><el-form-item label="类别">
            <el-select v-model="form.category" style="width:100%">
              <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="14"><el-form-item label="来源"><el-input v-model="form.source" placeholder="如 2026-11-04 培训试题.docx" /></el-form-item></el-col>
          <el-col :span="10"><el-form-item label="题目完整">
            <el-switch v-model="form.complete" active-text="含选项" inactive-text="待补选项" />
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="题目 JSON">
          <el-input v-model="form.theoryText" type="textarea" :rows="14" spellcheck="false"
            placeholder='{"single":[{"q":"题干","options":["A. ..","B. .."],"answer":"B"}],"multi":[],"judge":[]}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listTrainingBanks, getTrainingBank, createTrainingBank, updateTrainingBank, deleteTrainingBank,
} from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))

const CATEGORIES = ['组内培训', '科内培训', '实习讲课', '专项培训']

const list = ref([])
const loading = ref(false)
const category = ref('')
const keyword = ref('')

const viewVisible = ref(false)
const viewRow = ref({})
const viewData = ref({})

const formVisible = ref(false)
const saving = ref(false)
const form = ref({ id: null, topic: '', category: '组内培训', source: '', complete: true, theoryText: '{}' })

async function load() {
  loading.value = true
  try {
    const res = await listTrainingBanks({ category: category.value, q: keyword.value })
    list.value = res.items || []
  } finally {
    loading.value = false
  }
}

async function openView(row) {
  const d = await getTrainingBank(row.id)
  viewRow.value = { ...row, ...d }
  viewData.value = d.theory_json || {}
  viewVisible.value = true
}

async function openForm(row) {
  if (row) {
    const d = await getTrainingBank(row.id)
    form.value = {
      id: d.id, topic: d.topic, category: d.category, source: d.source || '',
      complete: d.complete !== false,
      theoryText: JSON.stringify(d.theory_json || {}, null, 2),
    }
  } else {
    form.value = { id: null, topic: '', category: '组内培训', source: '', complete: true, theoryText: '{\n  "single": [],\n  "multi": [],\n  "judge": []\n}' }
  }
  formVisible.value = true
}

async function save() {
  let theory
  try {
    theory = JSON.parse(form.value.theoryText || '{}')
  } catch (e) {
    ElMessage.error('题目 JSON 格式有误：' + e.message)
    return
  }
  if (!form.value.topic.trim()) {
    ElMessage.warning('请填写培训主题')
    return
  }
  saving.value = true
  try {
    const payload = {
      topic: form.value.topic, category: form.value.category, source: form.value.source,
      complete: form.value.complete, theory_json: theory,
    }
    if (form.value.id) await updateTrainingBank(form.value.id, payload)
    else await createTrainingBank(payload)
    ElMessage.success('已保存')
    formVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`删除「${row.topic}」题库？`, '提示', { type: 'warning' })
    await deleteTrainingBank(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) { /* cancel */ }
}

onMounted(load)
</script>

<style scoped>
.tb-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.tb-tip { color: #666; font-size: 13px; }
.tb-actions { display: flex; gap: 8px; align-items: center; }
.qitem { border-bottom: 1px dashed #ebeef5; padding: 8px 0; font-size: 13.5px; line-height: 1.7; }
.opt { color: #606266; font-size: 13px; margin-left: 16px; }
.ans { color: #16a34a; font-size: 13px; margin-top: 2px; }
</style>
