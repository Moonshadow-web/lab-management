<template>
  <div class="personnel-archive">
    <CrudTable
      :columns="columns"
      :fetch="fetch"
      search-placeholder="搜索姓名/职称/职务"
      :can-write="canWrite"
      @add="openForm()"
      @edit="openForm"
      @delete="onDelete"
      ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button link type="primary" @click="openDetail(row)">详情</el-button>
      </template>
    </CrudTable>

    <!-- 主表增改 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑人员档案' : '新增人员档案'" width="640px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="性别"><el-input v-model="form.gender" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="出生年月"><el-input v-model="form.birth_date" placeholder="如 1990-01" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="学历"><el-input v-model="form.education" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="职称"><el-input v-model="form.title" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="职务"><el-input v-model="form.position" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="政治面貌"><el-input v-model="form.political_status" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="组内职责"><el-input v-model="form.group_duty" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="参加工作时间"><el-input v-model="form.work_start" placeholder="如 2020-07" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="来院时间"><el-input v-model="form.hospital_join" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="来组时间"><el-input v-model="form.group_join" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="身份证号"><el-input v-model="form.id_card" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情：5 张子表 + 照片 -->
    <el-drawer v-model="detailVisible" :title="current?.name + ' · 人员档案详情'" size="70%">
      <template v-if="current">
        <div class="cert-row">
          <span class="cert-label">证书材料：</span>
          <EducationAttachmentList
            owner-type="personnel"
            :owner-id="current.id"
            kind="certificate"
            label="证书材料"
            accept=".jpg,.jpeg,.png,.pdf"
            :can-write="canWrite"
            @uploaded="onCertChange"
            ref="certRef"
          />
        </div>

        <el-tabs v-model="childTab">
          <el-tab-pane label="学历教育" name="edu">
            <ChildTable
              :owner-id="current.id" path="personnel-education"
              :fields="[{k:'school',l:'院校'},{k:'major',l:'专业'},{k:'degree',l:'学历/学位'},{k:'start_date',l:'开始'},{k:'end_date',l:'结束'},{k:'remark',l:'备注'}]"
              :can-write="canWrite" @changed="onPhotoChange"
            />
          </el-tab-pane>
          <el-tab-pane label="工作履历" name="work">
            <ChildTable
              :owner-id="current.id" path="personnel-work-exp"
              :fields="[{k:'org',l:'单位/科室'},{k:'post',l:'岗位'},{k:'start_date',l:'开始'},{k:'end_date',l:'结束'},{k:'remark',l:'备注'}]"
              :can-write="canWrite" @changed="onPhotoChange"
            />
          </el-tab-pane>
          <el-tab-pane label="资格证书" name="cert">
            <ChildTable
              :owner-id="current.id" path="personnel-certs"
              :fields="[{k:'cert_name',l:'证书名称'},{k:'cert_no',l:'编号'},{k:'issue_org',l:'发证机构'},{k:'issue_date',l:'发证日期'},{k:'valid_until',l:'有效期至'},{k:'remark',l:'备注'}]"
              :can-write="canWrite" @changed="onPhotoChange"
            />
          </el-tab-pane>
          <el-tab-pane label="奖惩" name="reward">
            <ChildTable
              :owner-id="current.id" path="personnel-rewards"
              :fields="[{k:'reward_type',l:'类型'},{k:'title',l:'事项'},{k:'date',l:'日期'},{k:'org',l:'机构'},{k:'remark',l:'备注'}]"
              :can-write="canWrite" @changed="onPhotoChange"
            />
          </el-tab-pane>
          <el-tab-pane label="继续教育经历" name="eduexp">
            <ChildTable
              :owner-id="current.id" path="personnel-edu-exp"
              :fields="[{k:'name',l:'培训项目'},{k:'organizer',l:'组织方'},{k:'train_date',l:'日期'},{k:'hours',l:'学时'},{k:'credits',l:'学分'},{k:'cert_no',l:'证书编号'},{k:'remark',l:'备注'}]"
              :can-write="canWrite" @changed="onPhotoChange"
            />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import EducationAttachmentList from '../EducationAttachmentList.vue'
import ChildTable from './PersonnelChildTable.vue'
import { listPersonnel, createPersonnel, updatePersonnel, deletePersonnel, getPersonnel } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite('training'))
const tableRef = ref(null)
const certRef = ref(null)

const columns = [
  { prop: 'name', label: '姓名', width: 100 },
  { prop: 'gender', label: '性别', width: 70 },
  { prop: 'title', label: '职称', width: 110 },
  { prop: 'position', label: '职务', width: 110 },
  { prop: 'education', label: '学历', width: 110 },
  { prop: 'group_duty', label: '组内职责', minWidth: 120 },
  { prop: 'work_start', label: '参加工作时间', width: 120 },
  { prop: 'phone', label: '电话', width: 120 },
]

const formVisible = ref(false)
const form = ref(blank())
function blank() {
  return { id: null, name: '', gender: '', birth_date: '', education: '', title: '', position: '',
    political_status: '', group_duty: '', work_start: '', hospital_join: '', group_join: '',
    id_card: '', phone: '', remark: '' }
}
function openForm(row) {
  form.value = row ? { ...row } : blank()
  formVisible.value = true
}
async function save() {
  try {
    if (form.value.id) await updatePersonnel(form.value.id, form.value)
    else await createPersonnel(form.value)
    ElMessage.success('已保存')
    formVisible.value = false
    tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.name} 的档案？`, '提示', { type: 'warning' })
    await deletePersonnel(row.id)
    ElMessage.success('已删除')
    tableRef.value?.refresh()
  } catch (e) {}
}

const detailVisible = ref(false)
const current = ref(null)
const childTab = ref('edu')
async function openDetail(row) {
  const res = await getPersonnel(row.id)
  current.value = res
  detailVisible.value = true
}
function onCertChange() { certRef.value?.refresh() }

function fetch(params) { return listPersonnel(params) }
</script>

<style scoped>
.cert-row { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }
.cert-label { font-weight: 600; }
</style>
