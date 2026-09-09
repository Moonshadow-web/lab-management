<template>
  <div class="exam-answer" style="max-width:720px;margin:0 auto;padding:16px;">
    <h2 style="text-align:center;margin:0 0 4px;">岗前培训理论考核</h2>
    <div style="text-align:center;color:#666;font-size:13px;margin-bottom:12px;">
      {{ record.name || '' }}　{{ (record.positions_json || []).join('、') }}
    </div>

    <div v-if="submitted" style="text-align:center;padding:24px 0;">
      <h3 style="color:#16a34a;">提交成功</h3>
      <p style="font-size:18px;">理论得分：<b>{{ finalScore }}</b> / {{ fullScore }}</p>
      <p style="color:#888;">成绩已回写到岗前培训考核记录</p>
    </div>

    <template v-else>
      <div v-for="blk in blocks" :key="blk.post" style="margin-bottom:18px;">
        <h3 style="border-left:4px solid #2563eb;padding-left:8px;font-size:16px;">{{ blk.post }}</h3>
        <div v-if="blk.single.length">
          <div style="font-weight:600;margin:6px 0;">一、单选题</div>
          <div v-for="(t, i) in blk.single" :key="'s' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-radio-group v-model="answers[blk.post]['s' + i]">
              <el-radio v-for="o in t.options" :key="o" :value="o.slice(0, 1)" style="display:block;margin:2px 0;">{{ o }}</el-radio>
            </el-radio-group>
          </div>
        </div>
        <div v-if="blk.multi.length">
          <div style="font-weight:600;margin:6px 0;">二、多选题</div>
          <div v-for="(t, i) in blk.multi" :key="'m' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-checkbox-group v-model="answers[blk.post]['m' + i]">
              <el-checkbox v-for="o in t.options" :key="o" :value="o.slice(0, 1)" style="display:block;margin:2px 0;">{{ o }}</el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
        <div v-if="blk.judge.length">
          <div style="font-weight:600;margin:6px 0;">三、判断题</div>
          <div v-for="(t, i) in blk.judge" :key="'j' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-radio-group v-model="answers[blk.post]['j' + i]">
              <el-radio value="对">对</el-radio><el-radio value="错">错</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>
      <div style="text-align:center;">
        <el-button type="primary" size="large" @click="submit" :loading="saving">提交答卷</el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getPreJobAuth, updatePreJobAuth, listExamBank } from '../../api/education'

const route = useRoute()
const id = Number(route.params.id)
const record = ref({})
const blocks = ref([])
const answers = ref({})
const submitted = ref(false)
const saving = ref(false)
const finalScore = ref(0)
const fullScore = ref(0)

onMounted(async () => {
  try {
    const [rec, bankRes] = await Promise.all([getPreJobAuth(id), listExamBank({ page_size: 50 })])
    record.value = rec
    const bankMap = Object.fromEntries((bankRes.items || []).map((b) => [b.post, b]))
    blocks.value = (rec.positions_json || []).map((post) => {
      const T = (bankMap[post] || {}).theory_json || {}
      return { post, single: T.single || [], multi: T.multi || [], judge: T.judge || [] }
    })
    const a = {}
    blocks.value.forEach((b) => { a[b.post] = {} })
    answers.value = a
    fullScore.value = blocks.value.reduce((s, b) => s + b.single.length * 2 + b.multi.length * 4 + b.judge.length * 2, 0)
  } catch (e) { ElMessage.error('加载失败：' + (e.response?.data?.detail || e.message)) }
})

// 判分：单选2 / 多选4 / 判断2（与 PC 端一致）
function scoreOf() {
  let s = 0
  blocks.value.forEach((b) => {
    b.single.forEach((t, i) => { if (answers.value[b.post]?.['s' + i] === t.answer.slice(0, 1)) s += 2 })
    b.multi.forEach((t, i) => {
      const g = (answers.value[b.post]?.['m' + i] || []).slice().sort().join('')
      if (g && g === t.answer.split('').sort().join('')) s += 4
    })
    b.judge.forEach((t, i) => { if (answers.value[b.post]?.['j' + i] === t.answer) s += 2 })
  })
  return s
}

async function submit() {
  saving.value = true
  try {
    const sc = scoreOf()
    finalScore.value = sc
    const exam = JSON.parse(JSON.stringify(record.value.exam_json || {}))
    blocks.value.forEach((b) => {
      exam[b.post] = Object.assign({}, exam[b.post] || {}, { theoryAnswers: answers.value[b.post] })
    })
    await updatePreJobAuth(id, { exam_json: exam })
    submitted.value = true
  } catch (e) { ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message)) } finally { saving.value = false }
}
</script>
