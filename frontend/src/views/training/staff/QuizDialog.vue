<template>
  <el-dialog
    :model-value="visible"
    :title="`扫码答题 —— ${sessionName || ''}`"
    width="880px"
    top="5vh"
    destroy-on-close
    @update:model-value="(v) => emit('update:visible', v)"
    @open="load"
  >
    <div v-loading="loading">
      <!-- 尚未创建 -->
      <template v-if="!quiz">
        <el-alert type="info" :closable="false" show-icon
          title="本次培训还没有随堂测验。粘贴题目 JSON 后创建，学员扫码输入姓名即可作答（不限制参与人）。"
          style="margin-bottom:12px" />
        <el-form label-width="90px">
          <el-form-item label="测验标题">
            <el-input v-model="form.title" :placeholder="sessionName" />
          </el-form-item>
          <el-form-item label="题目 JSON">
            <el-input v-model="form.theoryText" type="textarea" :rows="14" spellcheck="false"
              placeholder='{"single":[{"q":"题干","options":["A. ..","B. .."],"answer":"B"}],"multi":[...],"judge":[{"q":"题干","answer":"对"}]}' />
          </el-form-item>
          <el-form-item label="分值">
            <span style="font-size:13px;color:#606266">
              单选 {{ form.score_single }} 分 / 多选 {{ form.score_multi }} 分 / 判断 {{ form.score_judge }} 分，合格 {{ form.pass_score }} 分
            </span>
          </el-form-item>
        </el-form>
        <el-button type="primary" :loading="saving" @click="createQuiz">创建测验</el-button>
      </template>

      <!-- 已创建 -->
      <template v-else>
        <el-row :gutter="18">
          <el-col :span="9" style="text-align:center">
            <img v-if="qr" :src="qr" alt="答题二维码" style="width:210px;height:210px;border:1px solid #eee;border-radius:8px" />
            <div style="font-size:12px;color:#909399;margin-top:6px">微信/浏览器扫码，输入姓名即可答题</div>
            <el-input :model-value="link" readonly size="small" style="margin-top:10px">
              <template #append>
                <el-button @click="copyLink">复制</el-button>
              </template>
            </el-input>
            <div style="margin-top:10px">
              <el-switch v-model="quiz.is_open" active-text="开放答题" inactive-text="已关闭"
                @change="toggleOpen" />
            </div>
            <div style="margin-top:10px">
              <el-button size="small" @click="showEditor = !showEditor">{{ showEditor ? '收起题目' : '编辑题目' }}</el-button>
              <el-button size="small" type="danger" plain @click="removeQuiz">删除测验</el-button>
            </div>
          </el-col>
          <el-col :span="15">
            <div class="stat">
              参与 <b>{{ records.total }}</b> 人 ·
              合格 <b>{{ records.passed }}</b> 人 ·
              合格率 <b>{{ records.pass_rate }}%</b> ·
              平均 <b>{{ records.avg_pct }}</b> 分
            </div>
            <div class="stat" style="margin-top:4px;color:#606266;">
              效果评价 <b>{{ records.eval_total || 0 }}</b> 人 ·
              满意率 <b>{{ records.eval_satisfy_rate || 0 }}%</b> ·
              平均 <b>{{ records.eval_avg || 0 }}</b> 分
            </div>
            <div style="margin-top:8px;">
              <el-button size="small" type="primary" plain :loading="genLoading" @click="generateSummary">
                生成成绩 / 评价汇总 Word
              </el-button>
              <span style="font-size:12px;color:#909399;margin-left:6px;">自动挂到培训记录附件</span>
            </div>

            <el-table :data="records.items" size="small" border max-height="300" style="margin-top:8px">
              <el-table-column type="index" label="#" width="46" align="center" />
              <el-table-column prop="name" label="姓名" width="110" />
              <el-table-column prop="score" label="得分" width="90" align="center">
                <template #default="{ row }">{{ row.score }} / {{ row.full }}</template>
              </el-table-column>
              <el-table-column prop="pct" label="百分制" width="80" align="center" />
              <el-table-column label="结果" width="80" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '合格' : '不合格' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="提交时间" min-width="140">
                <template #default="{ row }">{{ (row.submit_at || '').replace('T', ' ').slice(0, 16) }}</template>
              </el-table-column>
            </el-table>
            <div style="color:#909399;font-size:12px;margin-top:6px">
              共 {{ quiz.question_count }} 题；重复提交会新增记录（同一人多次作答以最高分为准自行取用）。
            </div>
          </el-col>
        </el-row>

        <div v-if="showEditor" style="margin-top:14px">
          <el-input v-model="form.theoryText" type="textarea" :rows="12" spellcheck="false" />
          <el-button type="primary" size="small" style="margin-top:8px" :loading="saving" @click="saveTheory">
            保存题目
          </el-button>
        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import QRCode from 'qrcode'
import {
  listTrainingQuizzes, getTrainingQuiz, createTrainingQuiz, updateTrainingQuiz,
  deleteTrainingQuiz, listQuizRecords, generateQuizSummary,
} from '../../../api/education'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sessionId: { type: [Number, String], default: null },
  sessionName: { type: String, default: '' },
})
const emit = defineEmits(['update:visible'])

const loading = ref(false)
const saving = ref(false)
const quiz = ref(null)
const qr = ref('')
const link = ref('')
const records = ref({ items: [], total: 0, passed: 0, pass_rate: 0, avg_pct: 0 })
const showEditor = ref(false)
const genLoading = ref(false)

const form = ref({
  title: '', theoryText: '',
  score_single: 6, score_multi: 8, score_judge: 6, pass_score: 60,
})

async function load() {
  if (!props.sessionId) return
  loading.value = true
  quiz.value = null
  form.value.title = `${props.sessionName || '培训'} 随堂测验`
  form.value.theoryText = ''
  try {
    const res = await listTrainingQuizzes({ session_id: props.sessionId })
    const item = (res.items || [])[0]
    if (item) {
      const detail = await getTrainingQuiz(item.id)
      quiz.value = { ...item, ...detail }
      form.value.title = detail.title || form.value.title
      form.value.score_single = detail.score_single
      form.value.score_multi = detail.score_multi
      form.value.score_judge = detail.score_judge
      form.value.pass_score = detail.pass_score
      form.value.theoryText = JSON.stringify(detail.theory_json || {}, null, 2)
      link.value = `${window.location.origin}/quiz/${item.id}`
      qr.value = await QRCode.toDataURL(link.value, { width: 220, margin: 1 })
      await loadRecords()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadRecords() {
  records.value = await listQuizRecords(quiz.value.id)
}


async function createQuiz() {
  let theory
  try {
    theory = JSON.parse(form.value.theoryText || '{}')
  } catch (e) {
    ElMessage.error('题目 JSON 格式有误：' + e.message)
    return
  }
  if (!(theory.single || theory.multi || theory.judge)) {
    ElMessage.warning('题目为空')
    return
  }
  saving.value = true
  try {
    await createTrainingQuiz({
      session_id: props.sessionId,
      title: form.value.title || props.sessionName,
      theory_json: theory,
      score_single: form.value.score_single,
      score_multi: form.value.score_multi,
      score_judge: form.value.score_judge,
      pass_score: form.value.pass_score,
      is_open: true,
    })
    ElMessage.success('测验已创建')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

async function saveTheory() {
  let theory
  try {
    theory = JSON.parse(form.value.theoryText || '{}')
  } catch (e) {
    ElMessage.error('题目 JSON 格式有误：' + e.message)
    return
  }
  saving.value = true
  try {
    await updateTrainingQuiz(quiz.value.id, { theory_json: theory })
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleOpen(v) {
  try {
    await updateTrainingQuiz(quiz.value.id, { is_open: v })
    ElMessage.success(v ? '已开放答题' : '已关闭答题')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function removeQuiz() {
  try {
    await ElMessageBox.confirm('删除测验会同时删除全部作答记录，确认？', '提示', { type: 'warning' })
    await deleteTrainingQuiz(quiz.value.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) { /* cancel */ }
}

async function generateSummary() {
  genLoading.value = true
  try {
    const res = await generateQuizSummary(props.sessionId)
    const n = (res.attachments || []).length
    ElMessage.success(n ? `已生成 ${n} 份汇总 Word，已挂到培训附件` : '已生成汇总')
    await loadRecords()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    genLoading.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(link.value)
    ElMessage.success('链接已复制')
  } catch (e) {
    ElMessage.warning('复制失败，请手动选中复制')
  }
}
</script>

<style scoped>
.stat { font-size: 13px; color: #303133; }
.stat b { color: #2563eb; font-size: 15px; margin: 0 2px; }
</style>
