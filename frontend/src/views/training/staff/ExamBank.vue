<template>
  <div class="exam-bank">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="color:#666;font-size:13px;">岗位考核方式与题库（岗前培训授权表单自动引用）</span>
      <el-button type="primary" :disabled="!canWrite" @click="openForm()">新增岗位题库</el-button>
    </div>
    <el-table :data="list" border size="small" v-loading="loading">
      <el-table-column prop="post" label="岗位" width="140" />
      <el-table-column label="考核方式" min-width="160">
        <template #default="{ row }"><el-tag v-for="m in row.methods_json" :key="m" size="small" style="margin-right:4px;">{{ m }}</el-tag></template>
      </el-table-column>
      <el-table-column label="口头问答" width="90"><template #default="{ row }">{{ (row.qa_json || []).length }} 题</template></el-table-column>
      <el-table-column label="实操要点" width="90"><template #default="{ row }">{{ (row.practical_json || []).length }} 项</template></el-table-column>
      <el-table-column label="理论题" width="90"><template #default="{ row }">{{ theoryCount(row) }} 题</template></el-table-column>
      <el-table-column prop="updated_at" label="更新" width="160" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!canWrite" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" :disabled="!canWrite" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="(form.id ? '编辑题库 · ' : '新增题库 · ') + form.post" width="880px" top="3vh">
      <el-form label-width="90px">
        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="岗位">
              <el-select v-model="form.post" style="width:100%"><el-option v-for="p in META" :key="p.name" :label="p.name" :value="p.name" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="14">
            <el-form-item label="考核方式">
              <el-select v-model="methods" multiple style="width:100%" placeholder="选 1-2 种"><el-option v-for="m in ALL_METHODS" :key="m" :label="m" :value="m" /></el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">口头问答 Q&A</el-divider>
        <div v-for="(qa, i) in qaList" :key="'qa' + i" style="display:flex;gap:6px;margin-bottom:6px;">
          <el-input v-model="qa.q" placeholder="问题" style="width:40%;" />
          <el-input v-model="qa.a" placeholder="参考答案要点" style="flex:1;" />
          <el-button link type="danger" @click="qaList.splice(i, 1)">删</el-button>
        </div>
        <el-button size="small" @click="qaList.push({ q: '', a: '' })">+ 加一问</el-button>

        <el-divider content-position="left">实操要点与打分（满分自动汇总，建议 100）</el-divider>
        <div v-for="(pt, i) in practicalList" :key="i" style="display:flex;gap:6px;margin-bottom:6px;align-items:center;">
          <span style="color:#888;">{{ i + 1 }}.</span>
          <el-input v-model="pt.point" placeholder="操作要点/打分点" style="flex:1;" />
          <el-input-number v-model="pt.score" :min="1" :max="100" size="small" style="width:100px;" />
          <el-button link type="danger" @click="practicalList.splice(i, 1)">删</el-button>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-button size="small" @click="practicalList.push({ point: '', score: 10 })">+ 加一点</el-button>
          <span>当前满分：<b>{{ practicalTotal }}</b></span>
        </div>

        <el-divider content-position="left">理论题（各 5 题为宜）</el-divider>
        <template v-for="sec in ['single', 'multi', 'judge']" :key="sec">
          <div style="font-weight:600;margin:8px 0 4px;">{{ { single: '单选', multi: '多选', judge: '判断' }[sec] }}</div>
          <div v-for="(t, i) in theoryList[sec]" :key="sec + i" style="border:1px solid #eee;border-radius:6px;padding:6px;margin-bottom:6px;">
            <div style="display:flex;gap:6px;">
              <el-input v-model="t.q" :placeholder="sec === 'judge' ? '判断题（答案 对/错）' : '题干'" style="flex:1;" />
              <el-button link type="danger" @click="theoryList[sec].splice(i, 1)">删</el-button>
            </div>
            <div v-if="sec !== 'judge'" style="display:flex;gap:6px;margin-top:4px;">
              <el-input v-for="(o, oi) in t.options" :key="oi" v-model="t.options[oi]" size="small" style="width:23%;" />
              <el-select v-if="sec === 'single'" v-model="t.answer" size="small" style="width:90px;" placeholder="答案">
                <el-option v-for="k in ['A', 'B', 'C', 'D']" :key="k" :label="k" :value="k" />
              </el-select>
              <el-select v-else v-model="t.answer" size="small" multiple style="width:180px;" placeholder="答案(可多选)">
                <el-option v-for="k in ['A', 'B', 'C', 'D']" :key="k" :label="k" :value="k" />
              </el-select>
            </div>
            <div v-else style="margin-top:4px;">
              <el-radio-group v-model="t.answer" size="small"><el-radio value="对">对</el-radio><el-radio value="错">错</el-radio></el-radio-group>
            </div>
          </div>
          <el-button size="small" @click="addTheory(sec)">+ 加一题</el-button>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GL070_POSITIONS as META } from './gl070Meta'
import { listExamBank, createExamBank, updateExamBank, deleteExamBank } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const ALL_METHODS = ['口头问答', '实操考核', '理论考核']
const list = ref([])
const loading = ref(false)
const visible = ref(false)
const methods = ref([])
const qaList = ref([])
const practicalList = ref([])
const theoryList = ref({ single: [], multi: [], judge: [] })
const form = ref({ id: null, post: '', remark: '' })

async function refresh() {
  loading.value = true
  try {
    const res = await listExamBank({ page_size: 50 })
    list.value = res.items || []
  } finally { loading.value = false }
}
refresh()

function theoryCount(row) {
  const t = row.theory_json || {}
  return (t.single || []).length + (t.multi || []).length + (t.judge || []).length
}
const practicalTotal = computed(() => practicalList.value.reduce((s, p) => s + (p.score || 0), 0))

function addTheory(sec) {
  if (sec === 'single') theoryList.value.single.push({ q: '', options: ['A ', 'B ', 'C ', 'D '], answer: 'A' })
  else if (sec === 'multi') theoryList.value.multi.push({ q: '', options: ['A ', 'B ', 'C ', 'D '], answer: ['A'] })
  else theoryList.value.judge.push({ q: '', answer: '对' })
}
function blankBank() {
  theoryList.value = { single: [], multi: [], judge: [] }
  addTheory('single'); addTheory('single'); addTheory('single'); addTheory('single'); addTheory('single')
  addTheory('multi'); addTheory('multi'); addTheory('multi'); addTheory('multi'); addTheory('multi')
  addTheory('judge'); addTheory('judge'); addTheory('judge'); addTheory('judge'); addTheory('judge')
  return { id: null, post: '', remark: '' }
}
function openForm(row) {
  if (row) {
    form.value = { id: row.id, post: row.post, remark: row.remark || '' }
    methods.value = [...(row.methods_json || [])]
    qaList.value = JSON.parse(JSON.stringify(row.qa_json || []))
    practicalList.value = JSON.parse(JSON.stringify(row.practical_json || []))
    const t = row.theory_json || {}
    theoryList.value = {
      single: JSON.parse(JSON.stringify(t.single || [])),
      multi: JSON.parse(JSON.stringify(t.multi || [])),
      judge: JSON.parse(JSON.stringify(t.judge || [])),
    }
  } else {
    form.value = blankBank()
    methods.value = ['实操考核']
    qaList.value = [{ q: '', a: '' }]
    practicalList.value = [{ point: '', score: 10 }]
  }
  visible.value = true
}
async function save() {
  if (!form.value.post) { ElMessage.error('请选择岗位'); return }
  const payload = {
    post: form.value.post,
    methods_json: methods.value,
    qa_json: qaList.value.filter((x) => x.q),
    practical_json: practicalList.value.filter((x) => x.point),
    theory_json: theoryList.value,
    remark: form.value.remark,
  }
  try {
    if (form.value.id) await updateExamBank(form.value.id, payload)
    else await createExamBank(payload)
    ElMessage.success('题库已保存'); visible.value = false; refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`删除「${row.post}」题库？`, '提示', { type: 'warning' })
    await deleteExamBank(row.id); ElMessage.success('已删除'); refresh()
  } catch (e) {}
}
</script>
