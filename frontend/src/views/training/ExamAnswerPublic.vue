<template>
  <div style="max-width:720px;margin:0 auto;padding:16px;">
    <h2 style="text-align:center;margin:0 0 4px;">岗前培训理论考核</h2>
    <div style="text-align:center;color:#888;font-size:12px;margin-bottom:14px;">请输入本人姓名，找到您的考核单后作答</div>

    <!-- 第一步：填姓名 -->
    <div v-if="step === 1">
      <el-input v-model="name" size="large" placeholder="请输入姓名" @keyup.enter="findMine" />
      <el-button type="primary" size="large" style="width:100%;margin-top:12px;" @click="findMine" :loading="loading">查找我的考核单</el-button>
    </div>

    <!-- 第二步：选择考核单 -->
    <div v-else-if="step === 2">
      <div v-if="!mine.length" style="text-align:center;color:#999;padding:20px 0;">
        未找到「{{ name }}」的考核单，请与组长确认姓名是否与系统一致
      </div>
      <el-radio-group v-else v-model="picked" style="width:100%;">
        <el-radio v-for="r in mine" :key="r.id" :value="r.id" style="display:block;margin:8px 0;">
          #{{ r.id }}　{{ r.name }}　{{ r.apply_date }}　{{ (r.positions_json || []).join('、') }}
        </el-radio>
      </el-radio-group>
      <div style="display:flex;gap:8px;margin-top:12px;">
        <el-button @click="step = 1">返回</el-button>
        <el-button type="primary" :disabled="!picked" @click="loadPaper" :loading="loading">开始答题</el-button>
      </div>
    </div>

    <!-- 第三步：答卷 -->
    <div v-else-if="step === 3">
      <div style="color:#666;font-size:13px;margin-bottom:8px;">姓名：{{ name }}　岗位：{{ (paper.positions || []).join('、') }}</div>
      <div v-for="blk in paper.papers || []" :key="blk.post" style="margin-bottom:16px;">
        <h3 style="border-left:4px solid #2563eb;padding-left:8px;font-size:16px;">{{ blk.post }}</h3>
        <div v-if="(blk.single || []).length">
          <div style="font-weight:600;margin:6px 0;">一、单选题</div>
          <div v-for="(t, i) in blk.single" :key="'s' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-radio-group v-model="answers[blk.post]['s' + i]">
              <el-radio v-for="o in t.options" :key="o" :value="o.slice(0, 1)" style="display:block;margin:2px 0;">{{ o }}</el-radio>
            </el-radio-group>
          </div>
        </div>
        <div v-if="(blk.multi || []).length">
          <div style="font-weight:600;margin:6px 0;">二、多选题</div>
          <div v-for="(t, i) in blk.multi" :key="'m' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-checkbox-group v-model="answers[blk.post]['m' + i]">
              <el-checkbox v-for="o in t.options" :key="o" :value="o.slice(0, 1)" style="display:block;margin:2px 0;">{{ o }}</el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
        <div v-if="(blk.judge || []).length">
          <div style="font-weight:600;margin:6px 0;">三、判断题</div>
          <div v-for="(t, i) in blk.judge" :key="'j' + i" style="margin-bottom:10px;">
            <div>{{ i + 1 }}. {{ t.q }}</div>
            <el-radio-group v-model="answers[blk.post]['j' + i]">
              <el-radio value="对">对</el-radio><el-radio value="错">错</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>
      <el-button type="primary" size="large" style="width:100%;" @click="submit" :loading="saving">提交答卷</el-button>
    </div>

    <!-- 完成 -->
    <div v-else style="text-align:center;padding:24px 0;">
      <h3 style="color:#16a34a;">提交成功</h3>
      <p style="font-size:18px;">理论得分（总分）：<b>{{ result.pct }}</b> / 100 分</p>
      <div v-for="(v, k) in result.detail || {}" :key="k" style="font-size:14px;color:#444;">
        {{ k }}：<b>{{ v.pct }}</b> / 100 分（原始 {{ v.score }}/{{ v.full }}）　合格线 60
      </div>
      <p style="color:#888;margin-top:8px;">成绩已回写到您的岗前培训考核记录</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

// 免登录：直接用 fetch，不走带鉴权拦截的 axios 实例
const BASE = window.location.origin + '/api/v1/education'
const step = ref(1)
const name = ref('')
const mine = ref([])
const picked = ref(null)
const paper = ref({})
const answers = ref({})
const loading = ref(false)
const saving = ref(false)
const result = ref({ score: 0, full: 0 })

async function findMine() {
  if (!name.value.trim()) { ElMessage.error('请输入姓名'); return }
  loading.value = true
  try {
    const r = await fetch(`${BASE}/public/pre-job-auths?name=${encodeURIComponent(name.value.trim())}`)
    const j = await r.json()
    mine.value = j.items || []
    picked.value = mine.value.length === 1 ? mine.value[0].id : null
    step.value = 2
  } catch (e) { ElMessage.error('查询失败') } finally { loading.value = false }
}

async function loadPaper() {
  loading.value = true
  try {
    const r = await fetch(`${BASE}/public/exam-paper/${picked.value}`)
    const j = await r.json()
    paper.value = j
    const a = {}
    ;(j.papers || []).forEach((b) => { a[b.post] = {} })
    answers.value = a
    step.value = 3
  } catch (e) { ElMessage.error('加载试卷失败') } finally { loading.value = false }
}

async function submit() {
  saving.value = true
  try {
    const r = await fetch(`${BASE}/public/exam-submit/${picked.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.value.trim(), answers: answers.value }),
    })
    const j = await r.json()
    if (!r.ok) { ElMessage.error(j.detail || '提交失败'); return }
    result.value = j
    step.value = 4
  } catch (e) { ElMessage.error('提交失败') } finally { saving.value = false }
}
</script>
