<template>
  <div class="reminder-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>提醒设置</span>
          <el-button size="small" :icon="Refresh" @click="loadAll">刷新</el-button>
        </div>
      </template>

      <el-tabs v-model="tab">
        <!-- 发送人 -->
        <el-tab-pane label="发送人" name="recipients">
          <div style="margin-bottom: 12px">
            <el-button size="small" type="primary" :icon="Plus" @click="onAddRecipient">新增发送人</el-button>
            <span style="font-size: 12px; color: #999; margin-left: 8px">收件人列表独立于系统账号，可自由增删。</span>
          </div>
          <el-table :data="recipients" v-loading="loadingR" stripe size="small">
            <el-table-column prop="name" label="姓名" width="140" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="phone" label="手机号" width="130" />
            <el-table-column prop="wx_uid" label="ServerChan Key" min-width="130" />
            <el-table-column prop="channels" label="渠道" width="100" />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.enabled" @change="(v) => onToggleRecipient(row, v)" />
              </template>
            </el-table-column>
            <el-table-column label="接收提醒类型" min-width="220">
              <template #default="{ row }">
                <template v-if="!row.rule_categories">
                  <el-tag size="small" type="info">未配置(不接收)</el-tag>
                </template>
                <template v-else>
                  <el-tag v-for="c in row.rule_categories.split(',').filter(Boolean)" :key="c" size="small" style="margin: 2px 4px 2px 0">
                    {{ categoryLabel(c) }}
                  </el-tag>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="备注" min-width="120" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="onEditRecipient(row)">编辑</el-button>
                <el-button size="small" text type="danger" @click="onDeleteRecipient(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 提醒类型 -->
        <el-tab-pane label="提醒类型" name="rules">
          <div style="margin-bottom: 12px">
            <el-button size="small" type="primary" :icon="Plus" @click="onAddRule">新增提醒类型</el-button>
            <span style="font-size: 12px; color: #999; margin-left: 8px">
              阈值=提前触发天数；升级里程碑=剩余天数降到这些值时再发（逗号分隔）。
            </span>
          </div>
          <el-table :data="rules" v-loading="loadingRule" stripe size="small">
            <el-table-column prop="label" label="名称" width="160" />
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.ref_kind === 'eqa' ? 'warning' : 'success'">
                  {{ row.ref_kind === 'eqa' ? '质评上报' : '仪器校准' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.enabled" @change="(v) => onToggleRule(row, v)" />
              </template>
            </el-table-column>
            <el-table-column prop="lead_days" label="提前天数" width="90" />
            <el-table-column prop="escalate_days_left" label="升级里程碑" width="110" />
            <el-table-column prop="scope_values" label="范围" min-width="120" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text @click="onEditRule(row)">编辑</el-button>
                <el-button size="small" text type="danger" @click="onDeleteRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 执行与记录 -->
        <el-tab-pane label="执行与记录" name="run">
          <div style="margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap">
            <el-button type="primary" :loading="running" @click="onRun(false)">立即检查并发送</el-button>
            <el-button :loading="running" @click="onRun(true)">仅预览(不发信)</el-button>
            <el-button :loading="testingMail" @click="onTestMail">发送测试邮件到 815268425@qq.com</el-button>
            <el-button @click="loadLog">刷新记录</el-button>
          </div>
          <el-alert v-if="runResult" :type="(runResult.emails_sent || runResult.wx_sent) ? 'success' : 'info'" :closable="false"
            :title="`规则 ${runResult.rules} 条 · 本次发送事项 ${runResult.items_sent} · 邮件 ${runResult.emails_sent} 人 · 微信 ${runResult.wx_sent || 0} 人`" />

          <template v-if="previewList.length">
            <div style="margin: 14px 0 6px; font-weight: 600">预览（将发送以下内容）</div>
            <el-table :data="previewList" stripe size="small">
              <el-table-column prop="rule" label="规则" width="150" />
              <el-table-column prop="title" label="标题" min-width="220" />
              <el-table-column prop="message" label="说明" min-width="200" />
              <el-table-column prop="days_left" label="剩余天" width="80" />
              <el-table-column label="会发信" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.will_send ? 'danger' : 'info'">{{ row.will_send ? '是' : '否' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <div style="margin: 18px 0 6px; font-weight: 600">最近发送记录</div>
          <el-table :data="sendLog" v-loading="loadingLog" stripe size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="rule_id" label="规则" width="70" />
            <el-table-column prop="ref_type" label="类型" width="100" />
            <el-table-column prop="ref_id" label="关联ID" width="80" />
            <el-table-column prop="send_count" label="已发次数" width="90" />
            <el-table-column prop="sent_milestones" label="已发里程碑" width="130" />
            <el-table-column label="最近发送" min-width="160">
              <template #default="{ row }">{{ row.last_sent_at || '—' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.resolved ? 'success' : 'warning'">{{ row.resolved ? '已解决' : '进行中' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 发送人 编辑 -->
    <el-dialog v-model="showRecipient" :title="editingRecipient?.id ? '编辑发送人' : '新增发送人'" width="460px">
      <el-form :model="recipientForm" label-width="80px">
        <el-form-item label="姓名" required><el-input v-model="recipientForm.name" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="recipientForm.email" placeholder="接收提醒的邮箱" /></el-form-item>
        <el-form-item label="手机号"><el-input v-model="recipientForm.phone" placeholder="短信预留" /></el-form-item>
        <el-form-item label="ServerChan">
          <el-input v-model="recipientForm.wx_uid" placeholder="方糖 SendKey（登录 sctapi.ftqq.com 微信扫码复制）">
            <template #append>
              <el-button size="small" :loading="testWxLoading" @click="onTestWx">发送测试</el-button>
            </template>
          </el-input>
          <div style="margin-top: 6px">
            <span style="font-size: 12px; color: #999">填好 SendKey 后点「发送测试」验证微信是否收到；渠道需勾选含 serverchan。</span>
          </div>
        </el-form-item>
        <el-form-item label="渠道">
          <el-select v-model="recipientForm.channels" style="width: 100%">
            <el-option label="邮件 email" value="email" />
            <el-option label="邮件+微信 email,serverchan" value="email,serverchan" />
            <el-option label="微信 serverchan" value="serverchan" />
            <el-option label="邮件+短信 email,sms" value="email,sms" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="recipientForm.enabled" /></el-form-item>
        <el-form-item label="接收提醒">
          <el-checkbox-group v-model="recipientForm.rule_categories">
            <el-checkbox v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</el-checkbox>
          </el-checkbox-group>
          <div style="font-size:12px;color:#999;margin-top:4px">勾选该接收人需接收的提醒类型；全部留空 = 不接收任何提醒。</div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="recipientForm.note" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRecipient = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitRecipient">保存</el-button>
      </template>
    </el-dialog>

    <!-- 提醒类型 编辑 -->
    <el-dialog v-model="showRule" :title="editingRule?.id ? '编辑提醒类型' : '新增提醒类型'" width="480px">
      <el-form :model="ruleForm" label-width="96px">
        <el-form-item label="名称" required><el-input v-model="ruleForm.label" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="ruleForm.ref_kind" style="width: 100%">
            <el-option label="质评上报(eqa)" value="eqa" />
            <el-option label="仪器校准(calibration)" value="calibration" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="ruleForm.enabled" /></el-form-item>
        <el-form-item label="提前天数"><el-input-number v-model="ruleForm.lead_days" :min="1" :max="365" /></el-form-item>
        <el-form-item label="升级里程碑">
          <el-input v-model="ruleForm.escalate_days_left" placeholder="如 14,7（剩余天数降到这些值时再发）" />
        </el-form-item>
        <el-form-item label="范围字段">
          <el-select v-model="ruleForm.scope_kind" style="width: 100%">
            <el-option label="按专业组 group" value="group" />
            <el-option label="全部 all" value="all" />
          </el-select>
        </el-form-item>
        <el-form-item label="范围值">
          <el-input v-model="ruleForm.scope_values" placeholder="质评填 生化,凝血 / 免疫；全部留空" />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="ruleForm.note" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRule = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmitRule">保存</el-button>
      </template>
    </el-dialog>

    <!-- ServerChan 绑定无需二维码，SendKey 直接粘贴 -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listRecipients, createRecipient, updateRecipient, deleteRecipient,
  listRules, createRule, updateRule, deleteRule, runReminders, listSendLog,
  getRecipientWxTest,
} from '../api/reminders'
import { testEmail } from '../api/notifications'

const tab = ref('recipients')
const recipients = ref([])
const rules = ref([])
const sendLog = ref([])
const loadingR = ref(false)
const loadingRule = ref(false)
const loadingLog = ref(false)
const submitting = ref(false)
const running = ref(false)
const testingMail = ref(false)
const runResult = ref(null)
const previewList = ref([])

const categoryOptions = computed(() => rules.value.map(r => ({ value: r.category, label: r.label })))
function categoryLabel(cat) {
  const r = rules.value.find(x => x.category === cat)
  return r ? r.label : cat
}

const showRecipient = ref(false)
const editingRecipient = ref(null)
const recipientForm = ref({ name: '', email: '', phone: '', wx_uid: '', channels: 'email', enabled: true, rule_categories: [], note: '' })
const testWxLoading = ref(false)

const showRule = ref(false)
const editingRule = ref(null)
const ruleForm = ref({ label: '', ref_kind: 'eqa', enabled: true, lead_days: 14, escalate_days_left: '7', scope_kind: 'group', scope_values: '', note: '' })

async function loadAll() {
  loadingR.value = true; loadingRule.value = true
  try {
    recipients.value = await listRecipients()
    rules.value = await listRules()
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loadingR.value = false; loadingRule.value = false
  }
  await loadLog()
}

async function loadLog() {
  loadingLog.value = true
  try { sendLog.value = await listSendLog({ limit: 50 }) } catch {}
  finally { loadingLog.value = false }
}

// 发送人
function onAddRecipient() {
  editingRecipient.value = null
  recipientForm.value = { name: '', email: '', phone: '', channels: 'email', enabled: true, rule_categories: rules.value.map(r => r.category), note: '' }
  showRecipient.value = true
}
function onEditRecipient(row) {
  editingRecipient.value = row
  recipientForm.value = { ...row, wx_uid: row.wx_uid || '', rule_categories: (row.rule_categories || '').split(',').filter(Boolean) }
  showRecipient.value = true
}
async function onSubmitRecipient() {
  if (!recipientForm.value.name) { ElMessage.warning('请填写姓名'); return }
  const payload = { ...recipientForm.value, rule_categories: (recipientForm.value.rule_categories || []).join(',') }
  submitting.value = true
  try {
    if (editingRecipient.value?.id) {
      await updateRecipient(editingRecipient.value.id, payload)
    } else {
      await createRecipient(payload)
    }
    ElMessage.success('已保存')
    showRecipient.value = false
    await loadAll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally { submitting.value = false }
}
async function onToggleRecipient(row, v) {
  try { await updateRecipient(row.id, { enabled: v }); ElMessage.success(v ? '已启用' : '已停用') }
  catch { ElMessage.error('操作失败') }
}
async function onDeleteRecipient(row) {
  try {
    await ElMessageBox.confirm(`确认删除发送人 ${row.name}？`, '删除', { type: 'error' })
    await deleteRecipient(row.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

// 微信(ServerChan)测试发送
async function onTestWx() {
  const id = editingRecipient.value?.id
  if (!id) { ElMessage.warning('请先保存接收人再发送测试'); return }
  if (!recipientForm.value.wx_uid) { ElMessage.warning('请先填写 ServerChan SendKey'); return }
  testWxLoading.value = true
  try {
    await getRecipientWxTest(id)
    ElMessage.success('测试微信已发送，请查看微信是否收到')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally { testWxLoading.value = false }
}

// 提醒类型
function onAddRule() {
  editingRule.value = null
  ruleForm.value = { label: '', ref_kind: 'eqa', enabled: true, lead_days: 14, escalate_days_left: '7', scope_kind: 'group', scope_values: '', note: '' }
  showRule.value = true
}
function onEditRule(row) {
  editingRule.value = row
  ruleForm.value = { ...row }
  showRule.value = true
}
async function onSubmitRule() {
  if (!ruleForm.value.label) { ElMessage.warning('请填写名称'); return }
  submitting.value = true
  try {
    if (editingRule.value?.id) {
      await updateRule(editingRule.value.id, ruleForm.value)
    } else {
      await createRule(ruleForm.value)
    }
    ElMessage.success('已保存')
    showRule.value = false
    await loadAll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally { submitting.value = false }
}
async function onToggleRule(row, v) {
  try { await updateRule(row.id, { enabled: v }); ElMessage.success(v ? '已启用' : '已停用') }
  catch { ElMessage.error('操作失败') }
}
async function onDeleteRule(row) {
  try {
    await ElMessageBox.confirm(`确认删除提醒类型 ${row.label}？`, '删除', { type: 'error' })
    await deleteRule(row.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

// 执行
async function onRun(dry) {
  running.value = true
  runResult.value = null
  previewList.value = []
  try {
    const res = await runReminders({ dry_run: dry, as_of: '' })
    runResult.value = res
    previewList.value = res.planned || []
    if (dry) ElMessage.success(`预览完成，计划发送 ${previewList.value.filter(p => p.will_send).length} 条`)
    else ElMessage.success(`执行完成，成功发信 ${res.emails_sent} 人`)
    await loadLog()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '执行失败')
  } finally { running.value = false }
}
async function onTestMail() {
  testingMail.value = true
  try {
    const res = await testEmail('815268425@qq.com')
    if (res?.sent) ElMessage.success('测试邮件已发送，请查收 815268425@qq.com')
    else ElMessage.warning('SMTP 未配置或发送失败：' + (res?.detail || ''))
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally { testingMail.value = false }
}

onMounted(loadAll)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
