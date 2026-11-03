<template>
  <div class="quiz-page">
    <div class="quiz-card" v-loading="loading">
      <div class="quiz-head">
        <h2>{{ paper.title || '培训随堂测验' }}</h2>
        <div class="quiz-sub" v-if="paper.id">
          共 {{ totalCount }} 题 · 满分 100 分 · 合格 {{ paper.pass_score }} 分
        </div>
      </div>

      <!-- 答题 -->
      <template v-if="step === 'answer'">
        <div class="name-row">
          <label>姓名</label>
          <el-input v-model="name" placeholder="请输入姓名（用于登记成绩）" clearable />
        </div>

        <template v-if="paper.single && paper.single.length">
          <h3 class="sec">一、单选题（每题 {{ paper.score_single }} 分）</h3>
          <div v-for="(q, i) in paper.single" :key="'s' + i" class="qbox">
            <div class="qtext"><b>{{ i + 1 }}.</b> {{ q.q }}</div>
            <el-radio-group v-model="answers['s' + i]" class="opts">
              <el-radio v-for="(o, oi) in q.options" :key="oi" :value="letter(oi)" class="opt">{{ o }}</el-radio>
            </el-radio-group>
          </div>
        </template>

        <template v-if="paper.multi && paper.multi.length">
          <h3 class="sec">二、多选题（每题 {{ paper.score_multi }} 分，多选少选均不得分）</h3>
          <div v-for="(q, i) in paper.multi" :key="'m' + i" class="qbox">
            <div class="qtext"><b>{{ i + 1 }}.</b> {{ q.q }}</div>
            <el-checkbox-group v-model="answers['m' + i]" class="opts">
              <el-checkbox v-for="(o, oi) in q.options" :key="oi" :value="letter(oi)" class="opt">{{ o }}</el-checkbox>
            </el-checkbox-group>
          </div>
        </template>

        <template v-if="paper.judge && paper.judge.length">
          <h3 class="sec">三、判断题（每题 {{ paper.score_judge }} 分）</h3>
          <div v-for="(q, i) in paper.judge" :key="'j' + i" class="qbox">
            <div class="qtext"><b>{{ i + 1 }}.</b> {{ q.q }}</div>
            <el-radio-group v-model="answers['j' + i]" class="opts">
              <el-radio value="对" class="opt">正确（√）</el-radio>
              <el-radio value="错" class="opt">错误（×）</el-radio>
            </el-radio-group>
          </div>
        </template>

        <h3 class="sec">四、培训效果评价</h3>
        <div class="eval-box">
          <div class="eval-q">本次培训对您掌握该内容的帮助程度：</div>
          <el-rate v-model="satisfaction" :texts="['很差','较差','一般','满意','非常满意']" show-text />
          <el-input v-model="comment" type="textarea" :rows="2" maxlength="300" show-word-limit
            placeholder="意见与建议（选填）" style="margin-top:8px" />
        </div>

        <el-button type="primary" size="large" style="width:100%;margin-top:18px" :loading="saving" @click="submit">
          提交答卷
        </el-button>
        <div class="tip">提交后可查看得分与每题对错</div>
      </template>

      <!-- 结果 -->
      <template v-else>
        <div class="result">
          <div class="score">{{ result.pct }}<span>分</span></div>
          <div class="verdict" :class="result.passed ? 'ok' : 'bad'">
            {{ result.passed ? '合格' : '未合格' }}（合格线 {{ result.pass_score }} 分）
          </div>
          <div class="raw">{{ result.name }}：{{ result.score }} / {{ result.full }} 分</div>
          <div class="raw" v-if="satisfaction">培训效果评价：{{ satisfaction }} 分（已记录）</div>
        </div>

        <h3 class="sec">答题详情</h3>
        <div v-for="it in result.review || []" :key="it.type + it.no"
             :class="['rv', it.ok ? 'rv-ok' : 'rv-bad']">
          <div class="rv-q">
            <span class="mark">{{ it.ok ? '✓' : '✗' }}</span>
            <b>{{ it.no }}.</b> {{ it.q }}
          </div>
          <div v-if="it.options && it.options.length" class="rv-opts">
            <div v-for="(o, oi) in it.options" :key="oi">{{ o }}</div>
          </div>
          <div class="rv-ans">
            你的答案：<b :class="it.ok ? 'ok' : 'bad'">{{ it.picked || '未作答' }}</b>
            <span style="margin-left:14px">正确答案：<b class="ok">{{ it.answer }}</b></span>
          </div>
        </div>

        <el-button style="width:100%;margin-top:16px" @click="restart">再答一次</el-button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const route = useRoute()
const quizId = route.params.id

const loading = ref(false)
const saving = ref(false)
const step = ref('answer')
const paper = ref({})
const name = ref('')
const answers = ref({})
const result = ref({})
const satisfaction = ref(0)
const comment = ref('')

const totalCount = computed(() =>
  (paper.value.single?.length || 0) + (paper.value.multi?.length || 0) + (paper.value.judge?.length || 0))

function letter(i) {
  return String.fromCharCode(65 + i)
}

async function load() {
  loading.value = true
  try {
    paper.value = await request.get(`/api/v1/education/public/quiz/${quizId}`)
    if (paper.value.title) document.title = paper.value.title
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '试卷加载失败')
  } finally {
    loading.value = false
  }
}

function validate() {
  if (!name.value.trim()) {
    ElMessage.warning('请先填写姓名')
    return false
  }
  const missing = []
  ;(paper.value.single || []).forEach((_, i) => {
    if (!answers.value['s' + i]) missing.push(`单选第 ${i + 1} 题`)
  })
  ;(paper.value.multi || []).forEach((_, i) => {
    if (!(answers.value['m' + i] || []).length) missing.push(`多选第 ${i + 1} 题`)
  })
  ;(paper.value.judge || []).forEach((_, i) => {
    if (!answers.value['j' + i]) missing.push(`判断第 ${i + 1} 题`)
  })
  if (missing.length) {
    ElMessage.warning(`还有 ${missing.length} 题未作答：${missing.slice(0, 3).join('、')}${missing.length > 3 ? ' 等' : ''}`)
    return false
  }
  if (!satisfaction.value) {
    ElMessage.warning('请先完成培训效果评价（选择满意度）')
    return false
  }
  return true
}

async function submit() {
  if (!validate()) return
  saving.value = true
  try {
    result.value = await request.post(`/api/v1/education/public/quiz/${quizId}/submit`, {
      name: name.value.trim(),
      answers: answers.value,
      eval: { satisfaction: satisfaction.value, comment: comment.value.trim() },
      source: 'qr',
    })
    step.value = 'result'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    saving.value = false
  }
}

function restart() {
  step.value = 'answer'
  answers.value = {}
  result.value = {}
  satisfaction.value = 0
  comment.value = ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(load)
</script>

<style scoped>
.quiz-page {
  min-height: 100vh;
  background: #f2f5fa;
  padding: 16px 12px 40px;
}
.quiz-card {
  max-width: 720px;
  margin: 0 auto;
  background: #fff;
  border-radius: 10px;
  padding: 18px 16px 22px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
.quiz-head h2 { margin: 0 0 4px; font-size: 18px; }
.quiz-sub { color: #909399; font-size: 12.5px; }
.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 0 6px;
}
.name-row label { font-size: 14px; color: #303133; white-space: nowrap; }
.sec { font-size: 14.5px; margin: 20px 0 8px; border-left: 4px solid #2563eb; padding-left: 8px; }
.qbox { padding: 10px 0; border-bottom: 1px dashed #ebeef5; }
.qtext { font-size: 14px; line-height: 1.7; color: #303133; }
.opts { display: flex; flex-direction: column; align-items: stretch; margin-top: 6px; gap: 2px; }
.opt {
  height: auto !important;
  margin-right: 0 !important;
  padding: 3px 0;
  display: flex;
  align-items: flex-start;
  white-space: normal;
}
.opt :deep(.el-radio__input),
.opt :deep(.el-checkbox__input) { margin-top: 3px; flex-shrink: 0; }
.opt :deep(.el-radio__label),
.opt :deep(.el-checkbox__label) {
  font-size: 13.5px;
  line-height: 1.6;
  white-space: normal;
  word-break: break-word;
  padding-left: 6px;
}
.opt :deep(.el-checkbox) { display: flex; align-items: flex-start; height: auto; white-space: normal; }
.tip { text-align: center; color: #909399; font-size: 12px; margin-top: 8px; }
.eval-box { background: #f7f9fc; border-radius: 8px; padding: 12px; }
.eval-q { font-size: 14px; color: #303133; margin-bottom: 6px; }
.result { text-align: center; padding: 10px 0 6px; }
.score { font-size: 46px; font-weight: 700; color: #2563eb; line-height: 1.1; }
.score span { font-size: 16px; margin-left: 4px; }
.verdict { margin-top: 6px; font-size: 15px; font-weight: 600; }
.verdict.ok { color: #16a34a; }
.verdict.bad { color: #dc2626; }
.raw { color: #909399; font-size: 13px; margin-top: 4px; }
.rv { border-radius: 8px; padding: 10px; margin-bottom: 8px; border: 1px solid; }
.rv-ok { background: #f0fdf4; border-color: #bbf7d0; }
.rv-bad { background: #fef2f2; border-color: #fecaca; }
.rv-q { font-size: 13.5px; line-height: 1.6; }
.mark { font-weight: 700; margin-right: 6px; }
.rv-ok .mark { color: #16a34a; }
.rv-bad .mark { color: #dc2626; }
.rv-opts { font-size: 12.5px; color: #606266; margin: 6px 0 0 20px; line-height: 1.6; }
.rv-ans { font-size: 13px; margin: 6px 0 0 20px; color: #606266; }
.ok { color: #16a34a; }
.bad { color: #dc2626; }
</style>
