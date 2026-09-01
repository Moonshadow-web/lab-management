<template>
  <div class="auth-sheet">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/项目/仪器/授权人"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button link type="primary" @click="openDetail(row)">详情/附件</el-button>
      </template>
    </CrudTable>

    <el-dialog v-model="visible" :title="form.id ? '编辑授权记录' : '新增授权记录'" width="860px" top="2vh">
      <el-form :model="form" label-width="120px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="所在部门"><el-input v-model="form.department" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="岗位"><el-input v-model="form.post" placeholder="如 生化流水线岗" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">授权五要素</el-divider>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="项目·方法"><el-input v-model="form.project" placeholder="如 肝功能 / ALT" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="仪器"><el-input v-model="form.instrument" placeholder="如 罗氏 c701" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="权限等级">
              <el-select v-model="form.auth_scope" style="width:100%">
                <el-option label="操作（基础执行）" value="操作" />
                <el-option label="复核（结果审核）" value="复核" />
                <el-option label="签发（最终报告）" value="签发" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="授权生效"><el-input v-model="form.valid_from" placeholder="如 2026-01-15" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="授权到期（≤1年）"><el-input v-model="form.valid_until" placeholder="如 2027-01-14" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">监督期（CNAS "有条件授权"）</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="监督期起"><el-input v-model="form.supervised_from" placeholder="可选" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="监督期止"><el-input v-model="form.supervised_until" placeholder="可选" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="监督人"><el-input v-model="form.supervisor" placeholder="如 资深员工姓名" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">状态机 + 关联评估</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="有效" value="有效" />
                <el-option label="有条件（监督期内）" value="有条件" />
                <el-option label="暂停（PT/请假等）" value="暂停" />
                <el-option label="撤销（连续不通过/违规）" value="撤销" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16"><el-form-item label="状态变更原因"><el-input v-model="form.status_reason" placeholder="如 2026-Q2 PT-EQA 钾不合格，暂停 3 个月" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="关联评估单ID">
              <el-input v-model.number="form.source_assessment_id" type="number" placeholder="如 6" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="16"><el-form-item label="评估摘要（冗余展示）"><el-input v-model="form.source_assessment_text" placeholder="如 2026 年度能力评估-张三-95分" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">授权人（CNAS 要求：中级及以上 + 本领域 ≥3 年）</el-divider>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="授权签字人"><el-input v-model="form.authorizer" /></el-form-item></el-col>
          <el-col :span="10"><el-form-item label="授权人资质"><el-input v-model="form.authorizer_qualification" placeholder="如 副主任技师 / 本领域 12 年" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="授权日期"><el-input v-model="form.auth_date" placeholder="如 2026-01-15" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">授权前置条件（CNAS 6.2）</el-divider>
        <el-row :gutter="24">
          <el-col :span="8"><el-checkbox v-model="form.has_qualification">资质合规</el-checkbox></el-col>
          <el-col :span="8"><el-checkbox v-model="form.has_assessment_pass">培训与评估合格</el-checkbox></el-col>
          <el-col :span="8"><el-checkbox v-model="form.has_supervised_period">监督期表现</el-checkbox></el-col>
        </el-row>

        <el-form-item label="备注" style="margin-top:8px"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" :title="(current?.name || '授权详情') + ' · 授权记录'" width="760px">
      <el-descriptions :column="2" border v-if="current">
        <el-descriptions-item label="姓名">{{ current.name }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ current.department }}</el-descriptions-item>
        <el-descriptions-item label="岗位" :span="2">{{ current.post }}</el-descriptions-item>
        <el-descriptions-item label="项目·方法" :span="2">{{ current.project }}</el-descriptions-item>
        <el-descriptions-item label="仪器" :span="2">{{ current.instrument }}</el-descriptions-item>
        <el-descriptions-item label="权限等级"><el-tag :type="scopeTag(current.auth_scope)" effect="light">{{ current.auth_scope }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="有效期">{{ current.valid_from }} ~ {{ current.valid_until }}</el-descriptions-item>
        <el-descriptions-item label="监督期" :span="2">{{ current.supervised_from || '—' }} ~ {{ current.supervised_until || '—' }}　监督人：{{ current.supervisor || '—' }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusTag(current.status)" effect="dark">{{ current.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="状态变更原因">{{ current.status_reason || '—' }}</el-descriptions-item>
        <el-descriptions-item label="关联评估单" :span="2">
          {{ current.source_assessment_text || '—' }}
          <span v-if="current.source_assessment_id" style="color:#909399">（评估单 #{{ current.source_assessment_id }}）</span>
        </el-descriptions-item>
        <el-descriptions-item label="授权签字人">{{ current.authorizer }}</el-descriptions-item>
        <el-descriptions-item label="授权人资质">{{ current.authorizer_qualification }}</el-descriptions-item>
        <el-descriptions-item label="授权日期" :span="2">{{ current.auth_date }}</el-descriptions-item>
        <el-descriptions-item label="前置条件" :span="2">
          <el-tag v-if="current.has_qualification" type="success" size="small" effect="plain" style="margin-right:6px">资质合规</el-tag>
          <el-tag v-if="current.has_assessment_pass" type="success" size="small" effect="plain" style="margin-right:6px">评估合格</el-tag>
          <el-tag v-if="current.has_supervised_period" type="success" size="small" effect="plain" style="margin-right:6px">监督期</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ current.remark || '—' }}</el-descriptions-item>
      </el-descriptions>
      <el-divider content-position="left">授权扫描件/附件</el-divider>
      <EducationAttachmentList
        owner-type="auth_sheet" :owner-id="current?.id" kind="auth_doc"
        label="授权附件" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
        :can-write="canWrite"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import EducationAttachmentList from '../EducationAttachmentList.vue'
import { listAuthSheet, createAuthSheet, updateAuthSheet, deleteAuthSheet, getAuthSheet } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'name', label: '姓名', width: 90 },
  { prop: 'department', label: '部门', width: 110 },
  { prop: 'post', label: '岗位', width: 110, showOverflowTooltip: true },
  { prop: 'project', label: '项目·方法', width: 160, showOverflowTooltip: true },
  { prop: 'instrument', label: '仪器', width: 110, showOverflowTooltip: true },
  { prop: 'auth_scope', label: '权限', width: 80, align: 'center' },
  { prop: 'status', label: '状态', width: 100, align: 'center' },
  { prop: 'valid_until', label: '到期', width: 110, align: 'center' },
  { prop: 'authorizer', label: '授权人', width: 90 },
  { prop: 'auth_date', label: '授权日期', width: 110 },
]

function scopeTag(scope) {
  if (scope === '签发') return 'danger'
  if (scope === '复核') return 'warning'
  return 'info'
}
function statusTag(status) {
  if (status === '有效') return 'success'
  if (status === '有条件') return 'warning'
  if (status === '暂停') return 'info'
  if (status === '撤销') return 'danger'
  return 'info'
}

const visible = ref(false)
const form = ref(blank())
function blank() {
  return {
    id: null,
    name: '', department: '生化免疫组', post: '',
    project: '', instrument: '', auth_scope: '操作',
    valid_from: '', valid_until: '',
    supervised_from: '', supervised_until: '', supervisor: '',
    status: '有条件', status_reason: '',
    source_assessment_id: null, source_assessment_text: '',
    authorizer: '', authorizer_qualification: '', auth_date: '',
    has_qualification: false, has_assessment_pass: false, has_supervised_period: false,
    remark: '',
  }
}
function openForm(row) { form.value = row ? { ...row } : blank(); visible.value = true }
async function save() {
  try {
    if (form.value.id) await updateAuthSheet(form.value.id, form.value)
    else await createAuthSheet(form.value)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteAuthSheet(row.id); ElMessage.success('已删除'); tableRef.value?.refresh() } catch (e) {}
}

const detailVisible = ref(false)
const current = ref(null)
async function openDetail(row) { current.value = await getAuthSheet(row.id); detailVisible.value = true }

function fetch(params) { return listAuthSheet(params) }
</script>
