<template>
  <div class="cert-auth">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索申请人/内容"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button link type="primary" @click="printPx001(row)">打印审核表</el-button>
        <el-button link type="primary" @click="openDetail(row)">详情/附件</el-button>
      </template>
    </CrudTable>

    <el-dialog v-model="visible" :title="form.id ? '编辑独立上岗资格认证' : '新增独立上岗资格认证'" width="720px">
      <el-form :model="form" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="申请人"><el-input v-model="form.applicant" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="申请日期"><el-input v-model="form.apply_date" placeholder="如 2026-01-15" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="申请内容"><el-input v-model="form.apply_content" type="textarea" :rows="2" placeholder="申请独立上岗的岗位/仪器" /></el-form-item>
        <el-form-item label="理论考核"><el-input v-model="form.theory_eval" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="操作考核"><el-input v-model="form.operation_eval" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="组长意见"><el-input v-model="form.group_leader_opinion" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="主任意见"><el-input v-model="form.director_opinion" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%"><el-option label="待审核" value="待审核" /><el-option label="通过" value="通过" /><el-option label="不通过" value="不通过" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" :title="current?.applicant + ' · 认证详情'" width="640px">
      <el-descriptions :column="1" border v-if="current">
        <el-descriptions-item label="申请内容">{{ current.apply_content }}</el-descriptions-item>
        <el-descriptions-item label="理论考核">{{ current.theory_eval }}</el-descriptions-item>
        <el-descriptions-item label="操作考核">{{ current.operation_eval }}</el-descriptions-item>
        <el-descriptions-item label="组长意见">{{ current.group_leader_opinion }}</el-descriptions-item>
        <el-descriptions-item label="主任意见">{{ current.director_opinion }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ current.status }}</el-descriptions-item>
      </el-descriptions>
      <el-divider content-position="left">原始审核表扫描件/附件</el-divider>
      <EducationAttachmentList
        owner-type="cert_auth" :owner-id="current?.id" kind="cert_doc"
        label="审核表附件" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
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
import { printHtml } from '../../../utils/printHtml'
import { listCertAuth, createCertAuth, updateCertAuth, deleteCertAuth, getCertAuth } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'applicant', label: '申请人', width: 110 },
  { prop: 'apply_date', label: '申请日期', width: 120 },
  { prop: 'apply_content', label: '申请内容', minWidth: 200, showOverflowTooltip: true },
  { prop: 'status', label: '状态', width: 90 },
]

const visible = ref(false)
const form = ref(blank())
function blank() { return { id: null, applicant: '', apply_date: '', apply_content: '', theory_eval: '', operation_eval: '', group_leader_opinion: '', director_opinion: '', status: '待审核', remark: '' } }
function openForm(row) { form.value = row ? { ...row } : blank(); visible.value = true }
async function save() {
  try {
    if (form.value.id) await updateCertAuth(form.value.id, form.value)
    else await createCertAuth(form.value)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteCertAuth(row.id); ElMessage.success('已删除'); tableRef.value?.refresh() } catch (e) {}
}
const detailVisible = ref(false)
const current = ref(null)
async function openDetail(row) { current.value = await getCertAuth(row.id); detailVisible.value = true }

function fetch(params) { return listCertAuth(params) }

// ===== P1：PX-001 原表版式打印（BG-SM-PX-001 生化免疫组独立上岗资格认证审核表） =====
function esc(s) { return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }
function printPx001(row) {
  const html = `
  <h2 style="text-align:center;font-size:20px;letter-spacing:3px;margin:0 0 14px;">生化免疫组独立上岗资格认证审核表</h2>
  <table style="border:1.5px solid #333;font-size:13px;">
    <tr>
      <td class="lbl" style="width:90px;text-align:center;background:#f7f7f7;">申请人</td>
      <td style="width:200px;text-align:center;height:30px;">${esc(row.applicant)}</td>
      <td class="lbl" style="width:90px;text-align:center;background:#f7f7f7;">申请日期</td>
      <td style="text-align:center;">${esc(row.apply_date)}</td>
    </tr>
    <tr>
      <td class="lbl" style="text-align:center;background:#f7f7f7;">申请内容</td>
      <td colspan="3" style="height:86px;vertical-align:top;padding:8px 10px;">${esc(row.apply_content) || '描述独立上岗工作内容'}</td>
    </tr>
    <tr>
      <td class="lbl" style="text-align:center;background:#f7f7f7;">考核内容</td>
      <td colspan="3" style="height:120px;vertical-align:top;padding:8px 10px;">
        <b>理论考核</b>（答案见附件）<br>${esc(row.theory_eval)}<br>
        <b>操作考核</b><br>${esc(row.operation_eval)}<br>
        <span style="font-size:12px;color:#444;">附：考核内容应涵盖独立上岗工作内容全部；生免独立值班，则应包括血库和微生物考核部分</span>
      </td>
    </tr>
    <tr>
      <td class="lbl" style="text-align:center;background:#f7f7f7;">考核专业组<br>组长意见</td>
      <td colspan="3" style="height:130px;vertical-align:top;padding:8px 10px;">
        ${esc(row.group_leader_opinion)}<br><br>
        <span style="font-size:12px;color:#444;">附：简述理论和操作考核情况及成绩，判断是否可独立上岗。若是生免独立值班，则应包括血库和微生物组长意见。</span>
        <div style="margin-top:18px;text-align:right;">组长签字：　　　　　　日期：　　　　</div>
      </td>
    </tr>
    <tr>
      <td class="lbl" style="text-align:center;background:#f7f7f7;">主任意见</td>
      <td colspan="3" style="height:110px;vertical-align:top;padding:8px 10px;">
        ${esc(row.director_opinion)}
        <div style="margin-top:24px;text-align:right;">科主任签字：　　　　　　日期：　　　　</div>
      </td>
    </tr>
  </table>`
  printHtml('BG-SM-PX-001 独立上岗资格认证审核表', html)
}
</script>
