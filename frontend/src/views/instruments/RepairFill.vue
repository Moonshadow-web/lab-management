<template>
  <div class="repair-fill-page">
    <div class="rf-card">
      <div class="rf-head">
        <h2>仪器维修记录填写</h2>
        <div class="rf-sub">扫码填写 · 无需登录 · 提交后自动保存至仪器档案</div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" v-loading="true" style="height: 120px" />

      <!-- 链接无效 -->
      <el-result v-else-if="error" icon="warning" title="链接无效或已过期" :sub-title="error">
        <template #extra>
          <div class="rf-tip-line">请联系仪器管理员重新生成二维码。</div>
        </template>
      </el-result>

      <!-- 提交成功 -->
      <el-result v-else-if="submitted" icon="success" title="提交成功" sub-title="感谢配合！维修记录已保存，管理员可在系统中查看。">
        <template #extra>
          <el-button type="primary" @click="resetAll">再填一条</el-button>
        </template>
      </el-result>

      <!-- 填写表单 -->
      <template v-else>
        <div class="rf-inst">
          <div class="rf-inst-item"><b>设备名称：</b>{{ info.name || '—' }}</div>
          <div class="rf-inst-item"><b>设备编号：</b>{{ info.dept_no || '—' }}</div>
          <div class="rf-inst-item"><b>规格型号：</b>{{ info.model || '—' }}</div>
          <div class="rf-inst-item" v-if="info.location"><b>存放地点：</b>{{ info.location }}</div>
        </div>

        <el-form :model="form" label-width="110px" size="default" label-position="left">
          <el-form-item label="故障描述" required>
            <el-input v-model="form.fault_desc" type="textarea" :rows="3" placeholder="请详细描述故障内容" />
          </el-form-item>
          <el-form-item label="影响项目">
            <el-input v-model="form.affected_items" type="textarea" :rows="2" placeholder="受影响的具体项目（多个用逗号分隔）" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12" :xs="24">
              <el-form-item label="发现人">
                <el-input v-model="form.finder" placeholder="发现人姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="12" :xs="24">
              <el-form-item label="发现时间">
                <el-date-picker v-model="form.found_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择日期+时间" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12" :xs="24">
              <el-form-item label="通知维修时间">
                <el-date-picker v-model="form.notify_repair_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12" :xs="24">
              <el-form-item label="处理时间">
                <el-date-picker v-model="form.handled_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="故障原因及维修过程">
            <el-input v-model="form.cause_process" type="textarea" :rows="3" placeholder="故障处理办法、处理结果及完成时间" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12" :xs="24">
              <el-form-item label="维修人">
                <el-input v-model="form.repairer" placeholder="维修人姓名" />
              </el-form-item>
            </el-col>
            <el-col :span="12" :xs="24">
              <el-form-item label="恢复使用时间">
                <el-date-picker v-model="form.restored_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="排查后质控验证过程及结果">
            <el-input v-model="form.qc_verification" type="textarea" :rows="3" placeholder="样本选择、结果数据分析、影响评估等" />
          </el-form-item>
          <el-form-item label="签字">
            <el-input v-model="form.signer" placeholder="填写人签字（您的姓名）" />
          </el-form-item>
        </el-form>

        <div class="rf-actions">
          <el-button type="primary" size="large" :loading="submitting" style="width:100%" @click="submit">
            提交维修记录
          </el-button>
        </div>
        <div class="rf-note">提交后如需补充，管理员可在系统中编辑。</div>
      </template>
    </div>
    <div class="rf-footer">民航总医院检验科 · 仪器维修记录</div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const token = new URLSearchParams(window.location.search).get('token') || ''
const loading = ref(true)
const error = ref('')
const info = ref({})
const submitted = ref(false)
const submitting = ref(false)
const form = reactive({
  fault_desc: '', affected_items: '', finder: '', found_at: '',
  notify_repair_at: '', handled_at: '', cause_process: '', repairer: '',
  qc_verification: '', restored_at: '', signer: '',
})

async function loadInfo() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.get(`/api/v1/public/repairs/invite/${token}`)
    info.value = res || {}
  } catch (e) {
    error.value = e?.response?.data?.detail || '链接无效或已过期'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.fault_desc && !form.affected_items) {
    ElMessage.warning('请至少填写故障描述或影响项目')
    return
  }
  submitting.value = true
  try {
    await request.post(`/api/v1/public/repairs/invite/${token}`, { ...form })
    submitted.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

function resetAll() {
  submitted.value = false
  Object.assign(form, {
    fault_desc: '', affected_items: '', finder: '', found_at: '',
    notify_repair_at: '', handled_at: '', cause_process: '', repairer: '',
    qc_verification: '', restored_at: '', signer: '',
  })
}

onMounted(() => {
  if (!token) {
    error.value = '缺少链接参数，请重新扫码'
    loading.value = false
    return
  }
  loadInfo()
})
</script>

<style scoped>
.repair-fill-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 16px;
  box-sizing: border-box;
}
.rf-card {
  max-width: 640px;
  margin: 24px auto;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  box-sizing: border-box;
}
.rf-head {
  text-align: center;
  margin-bottom: 18px;
}
.rf-head h2 {
  margin: 0 0 6px;
  color: #303133;
}
.rf-sub {
  color: #909399;
  font-size: 13px;
}
.rf-inst {
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  padding: 10px 14px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.9;
  color: #303133;
}
.rf-inst-item b {
  color: #606266;
}
.rf-actions {
  margin-top: 8px;
}
.rf-note {
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 10px;
}
.rf-tip-line {
  color: #909399;
  font-size: 13px;
}
.rf-footer {
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 12px;
}
</style>
