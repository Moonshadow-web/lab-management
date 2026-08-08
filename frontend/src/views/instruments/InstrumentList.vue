<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      :extra-params="instrumentExtraParams"
      search-placeholder="搜索名称 / 编号 / 型号 / 负责人..."
      :show-add="auth.canWrite('instruments')"
      :can-write="auth.canWrite('instruments')"
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    >
      <template #toolbar-extra>
        <el-button type="warning" plain @click="openRepairSummary">汇总维修记录</el-button>
        <el-button v-if="auth.canWrite('instruments')" @click="importVisible = true">批量导入档案</el-button>
        <el-switch
          v-model="hideNonActive"
          active-text="仅看在用"
          inline-prompt
          style="--el-switch-on-color: #67c23a; margin-right: 4px"
          @change="onFilterChange"
        />
      </template>
      <template #row-extra="{ row }">
        <el-button
          link
          :type="row.calib_level === 'danger' ? 'danger' : row.calib_level === 'warning' ? 'warning' : 'primary'"
          @click="openCalib(row)"
        >
          校准记录
          <span v-if="row.calib_level === 'danger'" style="margin-left: 2px">●逾期</span>
          <span v-else-if="row.calib_level === 'warning'" style="margin-left: 2px">●临期</span>
        </el-button>
        <el-button link type="primary" @click="openArchive(row)">档案</el-button>
        <el-button link type="warning" @click="openRepair(row)">维修记录</el-button>
      </template>
    </CrudTable>

    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑仪器' : '新增仪器'"
      :form="form"
      :fields="fields"
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />

    <!-- 校准记录 -->
    <el-dialog v-model="calibOpen" :title="`校准记录 - ${calibInstrument?.name || ''}`" width="860px">
      <el-table :data="calibs" border stripe>
        <el-table-column prop="calibration_date" label="校准日期" width="120" />
        <el-table-column prop="next_due_date" label="下次到期" width="120" />
        <el-table-column prop="result" label="结果" width="90" show-overflow-tooltip />
        <el-table-column prop="agency" label="检定机构" width="100" show-overflow-tooltip />
        <el-table-column prop="cycle_months" label="周期(月)" width="80" align="center" />
        <el-table-column prop="operator" label="校准人" width="90" />
        <el-table-column label="报告" width="180" align="center">
          <template #default="{ row }">
            <el-button v-if="auth.canWrite('instruments') && !row.report_file_path" link type="primary" :loading="reportUploading && reportTarget.recId === row.id" @click="pickReportFile(row)">上传报告</el-button>
            <template v-else>
              <el-button link type="primary" @click="previewReport(row)">预览</el-button>
              <el-button link type="info" @click="downloadReport(row)">下载</el-button>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ row }">
            <el-button v-if="auth.canWrite('instruments')" link type="danger" @click="delCalib(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider v-if="auth.canWrite('instruments')">新增校准记录</el-divider>
      <el-form v-if="auth.canWrite('instruments')" :model="calibForm" label-width="100px" inline>
        <el-form-item label="校准日期" required>
          <el-date-picker v-model="calibForm.calibration_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="下次到期" required>
          <el-date-picker v-model="calibForm.next_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="检定机构">
          <el-input v-model="calibForm.agency" style="width: 120px" />
        </el-form-item>
        <el-form-item label="周期(月)">
          <el-input v-model="calibForm.cycle_months" style="width: 90px" placeholder="如 12" />
        </el-form-item>
        <el-form-item label="校准人">
          <el-input v-model="calibForm.operator" style="width: 120px" />
        </el-form-item>
        <el-form-item label="结果">
          <el-input v-model="calibForm.result" style="width: 160px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calibOpen = false">关闭</el-button>
        <el-button v-if="auth.canWrite('instruments')" type="primary" :loading="calibSubmitting" @click="addCalib">添加记录</el-button>
      </template>
    </el-dialog>

    <!-- 维修记录（BG-KS-CZ-909 仪器维修记录表） -->
    <el-dialog v-model="repairOpen" :title="`维修记录 - ${repairInstrument?.name || ''}`" width="900px" top="3vh">
      <div class="repair-meta">
        <b>设备名称：</b>{{ repairInstrument?.name || '—' }}　<b>设备编号：</b>{{ repairInstrument?.dept_no || '—' }}　<b>规格型号：</b>{{ repairInstrument?.model || '—' }}
        <el-button v-if="auth.canWrite('instruments')" size="small" type="warning" style="float:right" @click="openRepairQR">生成二维码</el-button>
      </div>
      <el-table :data="repairs" border stripe v-loading="repairLoading">
        <el-table-column type="index" label="序号" width="55" align="center" />
        <el-table-column prop="found_at" label="发现时间" width="150" />
        <el-table-column prop="fault_desc" label="故障描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="repairer" label="维修人" width="90" />
        <el-table-column prop="restored_at" label="恢复使用时间" width="150" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row: r }">
            <el-button v-if="auth.canWrite('instruments')" link type="primary" @click="editRepairRow(r)">编辑</el-button>
            <el-button v-if="auth.canWrite('instruments')" link type="danger" @click="delRepairRow(r)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!repairLoading && !repairs.length" description="暂无维修记录" :image-size="60" />
      <el-divider v-if="auth.canWrite('instruments')">
        {{ repairEditingId ? '编辑维修记录' : '新建维修记录' }}
      </el-divider>
      <RepairRecordForm v-if="auth.canWrite('instruments')" :form="repairForm" finder-placeholder="默认登录人" />
      <div class="repair-tip">
        <b>表格填写说明：</b><br />
        1、故障描述：请详细描述故障内容及影响到的项目。<br />
        2、故障原因及维修过程：详细说明故障处理办法、处理结果、处理完成的日期和时间。如有维修工单也可在工单上标明。<br />
        3、排查后性能验证过程及结果：<br />
        &nbsp;&nbsp;3.1 样本的选择：设备修复后，当故障对检验结果的准确性有影响时，根据影响的程度可选择可校准的项目实施校准验证、室内质控验证、至少 5 份标本与其他仪器的检测比对、以前检验过的样本留样再测等方式中的合适方式。前提是样本结果是正确的。<br />
        &nbsp;&nbsp;3.2 需要填写故障前后结果数据分析：<br />
        &nbsp;&nbsp;&nbsp;&nbsp;a) 实施评估的判断：分析仪器故障的类型对检验结果的准确性是否有影响，当没有影响时无须对故障前检验结果进行评估。当故障可能影响检测结果时需对故障前检验结果进行评估。<br />
        &nbsp;&nbsp;&nbsp;&nbsp;b) 在评估时，至少抽取仪器故障发生前的最后 5 份标本，相关检测项目重测一次。以该次检验结果为靶值、计算故障前检测结果与该次检测结果的相对百分偏倚。当检测项目有大于或等于 80% 标本的结果在允许相对百分偏倚范围内时，说明故障前检测结果未受影响；否则，再向前分批检测部分标本（每批至少 5 份标本）并进行分析，找出所有可能受影响的标本。重测所有这些标本或只重测当中结果在生物参考区间两端和医学决定水平附近的标本。<br />
        &nbsp;&nbsp;&nbsp;&nbsp;c) 当故障仪器有检测相同项目的另一相同型号仪器时，在确认其仪器性能正常的条件下，可以短时间内用其来进行仪器故障发生前标本的检测。<br />
        &nbsp;&nbsp;&nbsp;&nbsp;d) 当故障仪器唯一时，根据故障排除时间的长短，对故障前的标本做适当保存，确保标本的稳定性，待故障仪器的性能经确认正常后进行仪器故障发生前标本的检测。<br />
        &nbsp;&nbsp;3.3 经评估确认故障前检测结果未受影响，检验报告无须作任何处理；假如仪器设备故障会对之前的检测结果造成影响，当其影响到临床疾病诊断或治疗时，收回或适当标识已发出的不符合检验结果，重新发布正确报告，填写《不符合检测报告评审记录表》。
      </div>
      <template #footer>
        <el-button @click="repairOpen = false">关闭</el-button>
        <template v-if="auth.canWrite('instruments')">
          <el-button v-if="repairEditingId" @click="resetRepairForm">取消编辑</el-button>
          <el-button type="primary" :loading="repairSubmitting" @click="submitRepair">{{ repairEditingId ? '保存修改' : '添加记录' }}</el-button>
        </template>
      </template>
    </el-dialog>

    <!-- 扫码填写二维码 -->
    <el-dialog v-model="qrVisible" :title="`扫码填写维修记录 - ${qrInstrument?.name || ''}`" width="440px" top="8vh">
      <div style="text-align:center">
        <div v-if="qrImg"><img :src="qrImg" style="width:230px;height:230px" alt="二维码" /></div>
        <div v-else v-loading="true" style="height:230px" />
        <div class="qr-tip">工程师用微信 / 相机扫码即可<b>免登录</b>填写本仪器维修记录（链接 30 天内有效）</div>
        <div class="qr-url">{{ qrUrl }}</div>
      </div>
      <template #footer>
        <el-button @click="qrVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyQrUrl">复制链接</el-button>
      </template>
    </el-dialog>

    <!-- 汇总维修记录（跨仪器） -->
    <el-dialog v-model="summaryOpen" title="汇总维修记录" width="1100px" top="4vh">
      <div class="repair-summary-count">共 <b>{{ summaryRows.length }}</b> 条维修记录（按录入时间倒序）</div>
      <el-table :data="summaryRows" border stripe v-loading="summaryLoading" max-height="540">
        <el-table-column type="index" label="序号" width="55" align="center" />
        <el-table-column prop="instrument_name" label="仪器" width="180" show-overflow-tooltip />
        <el-table-column prop="instrument_model" label="型号" width="150" show-overflow-tooltip />
        <el-table-column prop="instrument_dept_no" label="编号" width="170" show-overflow-tooltip />
        <el-table-column prop="found_at" label="发现时间" width="140" />
        <el-table-column prop="fault_desc" label="故障描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="repairer" label="维修人" width="80" />
        <el-table-column prop="restored_at" label="恢复使用时间" width="140" />
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewRepairDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="summaryOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 维修记录详情（汇总入口查看） -->
    <el-dialog v-model="repairDetailOpen" :title="`维修记录详情 - ${repairDetailRow?.instrument_name || ''}`" width="860px" top="4vh">
      <el-descriptions :column="2" border v-if="repairDetailRow">
        <el-descriptions-item label="仪器">{{ repairDetailRow.instrument_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="编号">{{ repairDetailRow.instrument_dept_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ repairDetailRow.instrument_model || '—' }}</el-descriptions-item>
        <el-descriptions-item label="发现人">{{ repairDetailRow.finder || '—' }}</el-descriptions-item>
        <el-descriptions-item label="发现时间">{{ repairDetailRow.found_at || '—' }}</el-descriptions-item>
        <el-descriptions-item label="通知维修时间">{{ repairDetailRow.notify_repair_at || '—' }}</el-descriptions-item>
        <el-descriptions-item label="处理时间">{{ repairDetailRow.handled_at || '—' }}</el-descriptions-item>
        <el-descriptions-item label="恢复使用时间">{{ repairDetailRow.restored_at || '—' }}</el-descriptions-item>
        <el-descriptions-item label="维修人">{{ repairDetailRow.repairer || '—' }}</el-descriptions-item>
        <el-descriptions-item label="签字">{{ repairDetailRow.signer || '—' }}</el-descriptions-item>
        <el-descriptions-item label="影响项目" :span="2"><div class="detail-text">{{ repairDetailRow.affected_items || '—' }}</div></el-descriptions-item>
        <el-descriptions-item label="故障描述" :span="2"><div class="detail-text">{{ repairDetailRow.fault_desc || '—' }}</div></el-descriptions-item>
        <el-descriptions-item label="故障原因及维修过程" :span="2"><div class="detail-text">{{ repairDetailRow.cause_process || '—' }}</div></el-descriptions-item>
        <el-descriptions-item label="排查后质控验证" :span="2">
          <div class="detail-text" v-if="renderQcDetail(repairDetailRow.qc_detail)">{{ renderQcDetail(repairDetailRow.qc_detail) }}</div>
          <div class="detail-text" v-else>{{ repairDetailRow.qc_verification || '—' }}</div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="repairDetailOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 仪器档案详情抽屉（详情 / 预览 / 下载 / 导入 / 替换 / 删除） -->
    <el-drawer v-model="archiveDrawer" :title="`仪器档案 - ${archiveRow?.name || ''}`" :size="drawerSize">
      <el-descriptions title="档案详情" :column="descColumn" border>
        <el-descriptions-item label="设备名称">{{ archiveRow?.name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ archiveRow?.model || '—' }}</el-descriptions-item>
        <el-descriptions-item label="制造商">{{ archiveRow?.manufacturer || '—' }}</el-descriptions-item>
        <el-descriptions-item label="出厂编号">{{ archiveRow?.serial_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="供货商名称">{{ archiveRow?.supplier || '—' }}</el-descriptions-item>
        <el-descriptions-item label="联系人及电话">{{ archiveRow?.contact || '—' }}</el-descriptions-item>
        <el-descriptions-item label="设备编号">{{ archiveRow?.dept_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="存放地点">{{ archiveRow?.location || '—' }}</el-descriptions-item>
        <el-descriptions-item label="接收日期">{{ archiveRow?.purchase_date || '—' }}</el-descriptions-item>
        <el-descriptions-item label="投入使用日期">{{ archiveRow?.start_date || '—' }}</el-descriptions-item>
        <el-descriptions-item label="设备负责人">{{ archiveRow?.owner || '—' }}</el-descriptions-item>
        <el-descriptions-item label="日常管理人">{{ archiveRow?.daily_manager || '—' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>仪器档案文件</el-divider>
      <div v-if="archiveInfo.has_archive">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>已建档：{{ archiveInfo.original_filename }}</template>
          <div style="font-size: 12px; color: #888">
            大小：{{ formatSize(archiveInfo.file_size) }} ｜ 导入时间：{{ formatTime(archiveInfo.uploaded_at) }}
          </div>
        </el-alert>
        <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap">
          <el-button type="primary" @click="previewArchive">预览</el-button>
          <el-button @click="downloadArchive">下载</el-button>
          <el-button v-if="auth.canWrite('instruments')" type="warning" :loading="uploading" @click="pickArchiveFile">替换</el-button>
          <el-button v-if="auth.canWrite('instruments')" type="danger" @click="removeArchive">删除</el-button>
        </div>
      </div>
      <div v-else>
        <el-alert type="info" :closable="false" show-icon title="尚未导入仪器档案文件">
          <template #default>点击右侧「导入档案」上传该仪器的档案（.docx / .pdf / .doc）。</template>
        </el-alert>
        <div style="margin-top: 12px">
          <el-button v-if="auth.canWrite('instruments')" type="primary" :loading="uploading" @click="pickArchiveFile">导入档案</el-button>
        </div>
      </div>

      <el-divider>对应 SOP 文件（仪器作业指导书）</el-divider>
      <div v-loading="sopLoading">
        <el-table v-if="sopDocs.length" :data="sopDocs" border stripe size="small">
          <el-table-column prop="doc_number" label="编号" width="200" show-overflow-tooltip />
          <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
          <el-table-column label="操作" width="130" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="previewDoc(row)">预览</el-button>
              <el-button link type="primary" size="small" @click="downloadDoc(row)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂未匹配到对应的 SOP 文件" :image-size="80" />
      </div>

      <el-divider>操作 / 保养记录（关联本仪器的记录表格）</el-divider>
      <div v-loading="docsLoading">
        <el-table v-if="linkedDocs.length" :data="linkedDocs" border stripe size="small">
          <el-table-column prop="doc_number" label="编号" width="130" show-overflow-tooltip />
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="130" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="previewDoc(row)">预览</el-button>
              <el-button link type="primary" size="small" @click="downloadDoc(row)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无操作 / 保养记录关联到此仪器" :image-size="80" />
        <div v-if="linkedDocs.length" class="linked-count">
          共 <b>{{ linkedDocs.length }}</b> 份记录表格
        </div>
      </div>

      <el-divider>对应项目（使用本仪器的检验项目）</el-divider>
      <div v-loading="linkedLoading">
        <el-table v-if="linkedTestItems.length" :data="linkedTestItems" border stripe size="small" @row-click="goTestItem">
          <el-table-column prop="code" label="项目编号" width="110" show-overflow-tooltip />
          <el-table-column prop="name" label="项目名称" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span style="color: #409eff; cursor: pointer">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="类别" width="80" align="center" />
          <el-table-column prop="instrument_group" label="仪器组" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.instrument_group || row.instrument || '—' }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无项目关联到此仪器" :image-size="80" />
        <div v-if="linkedTestItems.length" class="linked-count">
          共 <b>{{ linkedTestItems.length }}</b> 个检验项目
        </div>
      </div>
    </el-drawer>

    <!-- 档案预览（docx 由 mammoth 转网页在浏览器内显示，无需下载；pdf 走浏览器原生阅读器） -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="82%" top="4vh" append-to-body>
      <div v-loading="previewing" class="doc-preview" v-html="previewHtml"></div>
    </el-dialog>

    <!-- 批量导入仪器档案 -->
    <el-dialog v-model="importVisible" title="批量导入仪器档案" width="580px">
      <el-form label-width="90px">
        <el-form-item label="档案目录">
          <el-input v-model="importPath" placeholder="如 E:\生免组管理体系文件\生免组仪器档案" />
        </el-form-item>
        <div style="font-size: 12px; color: #888; margin-bottom: 8px">
          程序会扫描该目录下所有 .docx / .pdf / .doc 文件，用文件名中的科室编号（如 MHZYY-JYK-SM-1001）自动匹配仪器。
        </div>
      </el-form>
      <div v-if="importResult">
        <el-alert type="success" :closable="false">
          成功导入 {{ importResult.imported }} 个，共扫描 {{ importResult.total_files }} 个文件。
        </el-alert>
        <div v-if="importResult.skipped.length" style="margin-top: 8px">
          <div style="font-weight: 600; margin-bottom: 4px">未匹配 / 跳过（{{ importResult.skipped.length }}）：</div>
          <ul style="max-height: 200px; overflow: auto; font-size: 12px; color: #666; padding-left: 18px">
            <li v-for="(s, i) in importResult.skipped" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>

    <input ref="fileInput" type="file" accept=".docx,.pdf,.doc" style="display: none" @change="onArchiveFileChange" />
    <input ref="reportInput" type="file" accept=".docx,.pdf,.doc" style="display: none" @change="onReportFileChange" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import mammoth from 'mammoth'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import {
  listInstruments, getInstrument, createInstrument, updateInstrument, deleteInstrument,
  listCalibrations, createCalibration, deleteCalibration,
  uploadCalibrationReport, downloadCalibrationReport, deleteCalibrationReport, getCalibrationsStatus,
  uploadInstrumentArchive, getInstrumentArchiveInfo, downloadInstrumentArchive,
  deleteInstrumentArchive, getArchivesStatus, importArchivesFolder,
  getInstrumentTestItems, getInstrumentDocuments, getInstrumentSopDocuments,
  listRepairs, createRepair, updateRepair, deleteRepair, createRepairInvite, listAllRepairs,
} from '../../api/instruments'
import QRCode from 'qrcode'
import RepairRecordForm from './RepairRecordForm.vue'
import { buildQcSummary } from '../../utils/repairQc'
import { fetchDocumentBlob, downloadBlob, previewBlob } from '../../api/documents'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const dialogVisible = ref(false)

// 仪器档案描述列表：桌面 2 列，窄屏（≤768px）改 1 列，避免标签/值被挤压
const descColumn = ref(typeof window !== 'undefined' && window.innerWidth <= 768 ? 1 : 2)
// 档案抽屉尺寸：桌面 640px，窄屏占满全屏（size 用内联 !important，CSS 覆盖不生效，故用响应式 prop）
const drawerSize = ref(typeof window !== 'undefined' && window.innerWidth <= 768 ? '100%' : '640px')
function syncMobileLayout() {
  const mobile = typeof window !== 'undefined' && window.innerWidth <= 768
  descColumn.value = mobile ? 1 : 2
  drawerSize.value = mobile ? '100%' : '640px'
}
onMounted(() => window.addEventListener('resize', syncMobileLayout))
onBeforeUnmount(() => window.removeEventListener('resize', syncMobileLayout))

// 一键隐藏非在用：开启时仅显示「在用」状态的仪器（走后端 status 过滤），默认开启
const hideNonActive = ref(true)
const instrumentExtraParams = computed(() => (hideNonActive.value ? { status: '在用' } : {}))
function onFilterChange() {
  crud.value?.refresh()
}

// 从「项目查询」点击关联仪器跳转而来：?focus=<instrument_id> 时自动打开该仪器档案
const route = useRoute()
const router = useRouter()
async function focusInstrument(id) {
  const numId = Number(id)
  if (!numId) return
  try {
    const inst = await getInstrument(numId)
    openArchive(inst)
  } catch (e) {
    ElMessage.warning('未找到对应仪器档案')
  }
}
onMounted(() => {
  const f = route.query.focus
  if (f) focusInstrument(f)
})
watch(
  () => route.query.focus,
  (nf) => {
    if (nf) focusInstrument(nf)
  }
)
const editingId = ref(null)
const submitting = ref(false)

const STATUS_OPTIONS = ['在用', '备用', '维修', '停用'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'name', label: '仪器名称' },
  { prop: 'dept_no', label: '科室编号' },
  { prop: 'model', label: '规格型号' },
  { prop: 'manufacturer', label: '生产厂家' },
  { prop: 'category', label: '类别' },
  { prop: 'serial_no', label: '出厂编号' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'location', label: '存放位置' },
  { prop: 'owner', label: '设备负责人' },
  { prop: 'daily_manager', label: '日常管理人' },
  { prop: 'supplier', label: '供货商名称' },
  { prop: 'contact', label: '联系人及电话' },
  { prop: 'purchase_date', label: '接收日期', type: 'date' },
  { prop: 'start_date', label: '投入使用日期', type: 'date' },
]

const rules = {
  name: [{ required: true, message: '请填写仪器名称', trigger: 'blur' }],
}

const columns = [
  { prop: 'name', label: '名称', minWidth: 150, tooltip: false },
  { prop: 'dept_no', label: '科室编号', minWidth: 140, tooltip: false },
  { prop: 'model', label: '型号', minWidth: 100, tooltip: false },
  { prop: 'manufacturer', label: '厂家', minWidth: 110, tooltip: false },
  { prop: 'serial_no', label: '出厂编号', minWidth: 100, tooltip: false },
  {
    prop: 'status', label: '状态', minWidth: 70,
    formatter: (row) => {
      const map = { 在用: 'success', 备用: 'info', 维修: 'warning', 停用: 'danger', 已停用: 'danger' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
  { prop: 'start_date', label: '启用时间', minWidth: 80, formatter: (row) => formatYearMonth(row.start_date) },
  { prop: 'owner', label: '负责人', minWidth: 80, tooltip: false },
  { prop: 'daily_manager', label: '日常管理人', minWidth: 80, formatter: (row) => row.daily_manager || '—', tooltip: false },
  { prop: 'calib_next', label: '下次校准', minWidth: 150,
    formatter: (row) => {
      if (!row.calib_next) return '<span style="color:#c0c4cc">—</span>'
      const lvl = row.calib_level
      const color = lvl === 'danger' ? '#f56c6c' : lvl === 'warning' ? '#e6a23c' : '#67c23a'
      const tag = lvl === 'danger' ? '逾期' : lvl === 'warning' ? '即将到期' : ''
      const badge = tag ? ` <span style="color:${color}">(${tag})</span>` : ''
      return `<span style="color:${color}">${row.calib_next}${badge}</span>`
    },
  },
]

// 启用日期取到「年-月」（兼容 YYYY-MM-DD 或已为 YYYY-MM）
function formatYearMonth(v) {
  if (!v) return '—'
  const m = String(v).slice(0, 7)
  return /^\d{4}-\d{2}$/.test(m) ? m : (v || '—')
}

const emptyForm = () => ({
  name: '', dept_no: '', model: '', manufacturer: '', category: '',
  serial_no: '', status: '在用', location: '', owner: '', daily_manager: '',
  supplier: '', contact: '', purchase_date: '', start_date: '', qc_instrument: false,
})

const form = reactive(emptyForm())

// 列表加载时合并建档状态 + 校准预警状态
async function fetch(params) {
  const res = await listInstruments(params)
  try {
    const status = await getArchivesStatus()
    const map = {}
    status.forEach((s) => { map[s.instrument_id] = s })
    ;(res.items || []).forEach((it) => {
      const s = map[it.id]
      it.has_archive = !!(s && s.has_archive)
      it.archive_name = s ? s.original_filename : ''
    })
  } catch (e) { /* 状态接口不可用时忽略，不影响列表 */ }
  try {
    const cstatus = await getCalibrationsStatus()
    const cmap = {}
    cstatus.forEach((c) => { cmap[c.instrument_id] = c })
    ;(res.items || []).forEach((it) => {
      const c = cmap[it.id]
      it.calib_next = c ? c.next_due_date : ''
      it.calib_level = c ? c.level : ''
    })
  } catch (e) { /* 校准状态接口不可用时忽略，不影响列表 */ }
  return res
}
function onAdd() {
  Object.assign(form, emptyForm())
  editingId.value = null
  dialogVisible.value = true
}
function onEdit(row) {
  Object.assign(form, emptyForm(), row)
  // 历史数据 qc_instrument 可能为 null，归一为布尔，避免回传 null 触发后端 422
  form.qc_instrument = row.qc_instrument ?? false
  editingId.value = row.id
  dialogVisible.value = true
}
async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) {
      await updateInstrument(editingId.value, { ...form })
    } else {
      await createInstrument({ ...form })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await deleteInstrument(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}

// 校准记录
const calibOpen = ref(false)
const calibInstrument = ref(null)
const calibs = ref([])
const calibSubmitting = ref(false)
const calibForm = reactive({ calibration_date: '', next_due_date: '', result: '', agency: '', cycle_months: '', operator: '' })

// 校准报告：上传 / 预览 / 下载
const reportUploading = ref(false)
const reportInput = ref(null)
const reportTarget = reactive({ recId: null })

function reportExt(row) {
  const name = row.report_filename || row.report_file_path || ''
  const m = /\.[^.]+$/.exec(name)
  return m ? m[0].toLowerCase() : ''
}

async function openCalib(row) {
  calibInstrument.value = row
  calibOpen.value = true
  await loadCalibs(row.id)
}
async function loadCalibs(id) {
  try {
    calibs.value = await listCalibrations(id)
  } catch (e) {
    calibs.value = []
  }
}
async function addCalib() {
  if (!calibForm.calibration_date || !calibForm.next_due_date) {
    ElMessage.warning('请填写校准日期与下次到期日')
    return
  }
  calibSubmitting.value = true
  try {
    await createCalibration(calibInstrument.value.id, { ...calibForm })
    ElMessage.success('已添加')
    Object.assign(calibForm, { calibration_date: '', next_due_date: '', result: '', agency: '', cycle_months: '', operator: '' })
    await loadCalibs(calibInstrument.value.id)
    crud.value?.refresh()
  } finally {
    calibSubmitting.value = false
  }
}
async function delCalib(row) {
  await ElMessageBox.confirm('确认删除该校准记录？', '提示', { type: 'warning' })
  await deleteCalibration(calibInstrument.value.id, row.id)
  ElMessage.success('已删除')
  await loadCalibs(calibInstrument.value.id)
  crud.value?.refresh()
}

// ---------------- 维修记录（BG-KS-CZ-909） ----------------
const repairOpen = ref(false)
const repairInstrument = ref(null)
const repairs = ref([])
const repairLoading = ref(false)
const repairSubmitting = ref(false)
const repairEditingId = ref(null)
const defaultSigner = computed(() => auth.user?.full_name || auth.user?.username || '')
const repairForm = reactive({
  fault_desc: '',
  affected_items: '',
  finder: '',
  found_at: '',
  notify_repair_at: '',
  handled_at: '',
  cause_process: '',
  repairer: '',
  qc_verification: '',
  qc_detail: null,
  restored_at: '',
  signer: '',
})
// 日期默认当日 00:00:00，时间由用户再填
function todayDefault() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} 00:00:00`
}
function resetRepairForm() {
  repairEditingId.value = null
  const td = todayDefault()
  Object.assign(repairForm, {
    fault_desc: '', affected_items: '', finder: defaultSigner.value, found_at: td,
    notify_repair_at: td, handled_at: td, cause_process: '', repairer: '',
    qc_verification: '', qc_detail: null, restored_at: td, signer: defaultSigner.value,
  })
}
async function loadRepairs(instrumentId) {
  repairLoading.value = true
  try {
    const data = await listRepairs(instrumentId)
    repairs.value = data || []
  } finally {
    repairLoading.value = false
  }
}
async function openRepair(row) {
  repairInstrument.value = row
  repairOpen.value = true
  resetRepairForm()
  await loadRepairs(row.id)
}
function editRepairRow(r) {
  repairEditingId.value = r.id
  Object.assign(repairForm, {
    fault_desc: r.fault_desc || '',
    affected_items: r.affected_items || '',
    finder: r.finder || defaultSigner.value,
    found_at: r.found_at || todayDefault(),
    notify_repair_at: r.notify_repair_at || todayDefault(),
    handled_at: r.handled_at || todayDefault(),
    cause_process: r.cause_process || '',
    repairer: r.repairer || '',
    qc_verification: r.qc_verification || '',
    qc_detail: (r.qc_detail && typeof r.qc_detail === 'object' && Object.keys(r.qc_detail).length) ? r.qc_detail : null,
    restored_at: r.restored_at || todayDefault(),
    signer: r.signer || defaultSigner.value,
  })
}
async function delRepairRow(r) {
  await ElMessageBox.confirm('确认删除该维修记录？', '提示', { type: 'warning' })
  await deleteRepair(repairInstrument.value.id, r.id)
  ElMessage.success('已删除')
  await loadRepairs(repairInstrument.value.id)
  crud.value?.refresh()
}
async function submitRepair() {
  if (!repairForm.fault_desc && !repairForm.affected_items) {
    ElMessage.warning('请至少填写故障描述或影响项目')
    return
  }
  repairSubmitting.value = true
  try {
    const payload = {
      ...repairForm,
      signer: repairForm.signer || defaultSigner.value,
      qc_verification: buildQcSummary(repairForm.qc_detail),
    }
    if (repairEditingId.value) {
      await updateRepair(repairInstrument.value.id, repairEditingId.value, payload)
      ElMessage.success('已保存修改')
    } else {
      await createRepair(repairInstrument.value.id, payload)
      ElMessage.success('已添加维修记录')
    }
    repairEditingId.value = null
    const td = todayDefault()
    Object.assign(repairForm, {
      fault_desc: '', affected_items: '', finder: defaultSigner.value, found_at: td,
      notify_repair_at: td, handled_at: td, cause_process: '', repairer: '',
      qc_verification: '', qc_detail: null, restored_at: td, signer: defaultSigner.value,
    })
    await loadRepairs(repairInstrument.value.id)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally {
    repairSubmitting.value = false
  }
}

// ---------------- 扫码填写二维码 ----------------
const qrVisible = ref(false)
const qrImg = ref('')
const qrUrl = ref('')
const qrInstrument = ref(null)
async function openRepairQR() {
  if (!repairInstrument.value) return
  qrInstrument.value = repairInstrument.value
  qrVisible.value = true
  qrImg.value = ''
  qrUrl.value = ''
  try {
    const res = await createRepairInvite(repairInstrument.value.id)
    const url = `${window.location.origin}/repair-fill?token=${res.token}`
    qrUrl.value = url
    qrImg.value = await QRCode.toDataURL(url, { width: 240, margin: 1 })
  } catch (e) {
    ElMessage.error('生成二维码失败：' + (e?.response?.data?.detail || e?.message || '未知错误'))
  }
}
async function copyQrUrl() {
  try {
    await navigator.clipboard.writeText(qrUrl.value)
    ElMessage.success('链接已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动复制链接')
  }
}

// ---------------- 汇总维修记录 ----------------
const summaryOpen = ref(false)
const summaryRows = ref([])
const summaryLoading = ref(false)
const repairDetailOpen = ref(false)
const repairDetailRow = ref(null)
async function openRepairSummary() {
  summaryOpen.value = true
  summaryLoading.value = true
  try {
    summaryRows.value = (await listAllRepairs()) || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally {
    summaryLoading.value = false
  }
}
function viewRepairDetail(row) {
  repairDetailRow.value = row
  repairDetailOpen.value = true
}
// 质控验证结构化数据 → 可读文本（详情展示）
function renderQcDetail(qd) {
  if (!qd || typeof qd !== 'object') return ''
  const lines = []
  const biasStr = (r) => {
    const s = parseFloat(r.sample)
    const v = parseFloat(r.result)
    if (isNaN(s) || isNaN(v) || s === 0) return ''
    return (((v - s) / s) * 100).toFixed(2) + '%'
  }
  const fmtTarget = (rows) => (rows || []).filter((r) => r.target !== '' || r.result !== '').map((r) => `靶值${r.target || '-'}/结果${r.result || '-'}/${r.control || '未判'}`).join('；')
  const fmtCmp = (rows) => (rows || []).filter((r) => r.sample !== '' || r.result !== '').map((r) => `样本${r.sample || '-'}/结果${r.result || '-'}/偏倚${biasStr(r) || '-'}/${r.accept || '未判'}`).join('；')
  if (qd.method === 'qc') {
    lines.push(`验证方式：室内质控验证；项目：${qd.qc?.project || '—'}`)
    lines.push(fmtTarget(qd.qc?.rows) || '（未填写行）')
  } else if (qd.method === 'compare') {
    lines.push(`验证方式：样本比对；项目：${qd.compare?.project || '—'}`)
    lines.push(fmtCmp(qd.compare?.rows) || '（未填写行）')
  } else if (qd.method === 'calibrate') {
    const c = qd.calibrate || {}
    const vals = (c.results || []).map((v) => parseFloat(v)).filter((n) => !isNaN(n))
    const target = parseFloat(c.target)
    const unc = parseFloat(c.uncertainty)
    let judge = ''
    if (vals.length) {
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length
      judge = isNaN(target) || isNaN(unc) ? `均值${mean.toFixed(2)}（待填靶值/不确定度）` : `${Math.abs(mean - target) <= unc ? '可接受' : '否'}（均值${mean.toFixed(2)}，靶值±不确定度范围 ${target}-${unc}~${target}+${unc}）`
    }
    lines.push(`验证方式：校准验证；项目：${c.project || '—'}；靶值：${c.target || '-'}；不确定度：±${c.uncertainty || '-'}；3次结果：${(c.results || []).filter((v) => v !== '').join('、') || '未填'}${judge ? `；判定：${judge}` : ''}`)
  } else {
    lines.push(`验证方式：${qd.method || '未选'}`)
  }
  lines.push(qd.affect_before
    ? `是否影响维修前检测结果：是（样本比对 项目：${qd.affect_compare?.project || '—'} → ${fmtCmp(qd.affect_compare?.rows) || '未填写行'}）`
    : '是否影响维修前检测结果：否')
  return lines.join('\n')
}

function pickReportFile(row) {
  reportTarget.recId = row.id
  reportInput.value?.click()
}
async function onReportFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file || !calibInstrument.value || reportTarget.recId == null) return
  reportUploading.value = true
  const recId = reportTarget.recId
  try {
    await uploadCalibrationReport(calibInstrument.value.id, recId, file)
    ElMessage.success('校准报告已保存')
    await loadCalibs(calibInstrument.value.id)
    crud.value?.refresh()
  } catch (err) {
    ElMessage.error('上传失败')
  } finally {
    reportUploading.value = false
    reportTarget.recId = null
  }
}
async function downloadReport(row) {
  if (!calibInstrument.value) return
  try {
    const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
    triggerDownload(blob, row.report_filename || 'calibration_report')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}
async function previewReport(row) {
  if (!calibInstrument.value || !row.report_file_path) return
  const ext = reportExt(row)
  const fname = row.report_filename || '校准报告预览'
  if (ext === '.pdf') {
    try {
      const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) {
      ElMessage.error('预览失败')
    }
    return
  }
  if (ext === '.docx') {
    previewVisible.value = true
    previewTitle.value = fname
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // 其他格式回退下载
  try {
    const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
    triggerDownload(blob, fname)
    ElMessage.info('该格式暂不支持在线预览，已为你下载文件')
  } catch (e) {
    ElMessage.error('预览失败')
  }
}

// ---------------- 仪器档案 ----------------
const archiveDrawer = ref(false)
const archiveRow = ref(null)
const archiveInfo = ref({ has_archive: false })
const uploading = ref(false)
const fileInput = ref(null)
const previewVisible = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')
const previewing = ref(false)

// 反向索引：本仪器对应的项目（与项目查询页「关联仪器」芯片对称）
const linkedTestItems = ref([])
const linkedLoading = ref(false)

// 反向索引：本仪器关联的操作/保养记录（记录表格，归属文件管理模块）
const linkedDocs = ref([])
const docsLoading = ref(false)

// 反向索引：本仪器对应的 SOP 文件（仪器作业指导书，按编号自动匹配）
const sopDocs = ref([])
const sopLoading = ref(false)

async function loadArchiveInfo(id) {
  try {
    archiveInfo.value = await getInstrumentArchiveInfo(id)
  } catch (e) {
    archiveInfo.value = { has_archive: false }
  }
}
async function loadLinkedTestItems(id) {
  linkedLoading.value = true
  try {
    linkedTestItems.value = await getInstrumentTestItems(id)
  } catch (e) {
    linkedTestItems.value = []
  } finally {
    linkedLoading.value = false
  }
}
async function loadLinkedDocs(id) {
  docsLoading.value = true
  try {
    linkedDocs.value = await getInstrumentDocuments(id)
  } catch (e) {
    linkedDocs.value = []
  } finally {
    docsLoading.value = false
  }
}
async function loadSopDocs(id) {
  sopLoading.value = true
  try {
    sopDocs.value = await getInstrumentSopDocuments(id)
  } catch (e) {
    sopDocs.value = []
  } finally {
    sopLoading.value = false
  }
}
async function openArchive(row) {
  archiveRow.value = row
  archiveDrawer.value = true
  await loadArchiveInfo(row.id)
  await loadLinkedTestItems(row.id)
  await loadLinkedDocs(row.id)
  await loadSopDocs(row.id)
}
// 操作/保养记录：预览（docx 用 mammoth 内嵌显示；pdf 走浏览器；其他回退）
async function previewDoc(row) {
  const fname = row.original_filename || row.title || ''
  const ext = (fname.split('.').pop() || '').toLowerCase()
  if (ext === 'pdf') {
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      previewBlob(blob)
    } catch (e) {
      ElMessage.error('文件不存在或预览失败')
    }
    return
  }
  if (ext === 'docx') {
    previewVisible.value = true
    previewTitle.value = row.title || fname || '预览'
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  try {
    const blob = await fetchDocumentBlob(row.id, 'preview')
    previewBlob(blob)
  } catch (e) {
    ElMessage.error('文件不存在或预览失败')
  }
}
async function downloadDoc(row) {
  try {
    const blob = await fetchDocumentBlob(row.id, 'download')
    downloadBlob(blob, row.original_filename || row.title)
  } catch (e) {
    ElMessage.error('文件不存在或下载失败')
  }
}
// 点击项目跳转项目查询页，并自动按项目名搜索定位
function goTestItem(item) {
  router.push({ path: '/test-items', query: { q: item.name } })
}
function pickArchiveFile() {
  fileInput.value?.click()
}
async function onArchiveFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file || !archiveRow.value) return
  uploading.value = true
  try {
    await uploadInstrumentArchive(archiveRow.value.id, file)
    ElMessage.success('档案已保存')
    await loadArchiveInfo(archiveRow.value.id)
    crud.value?.refresh()
  } catch (err) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}
async function downloadArchive() {
  if (!archiveRow.value) return
  try {
    const blob = await downloadInstrumentArchive(archiveRow.value.id)
    triggerDownload(blob, archiveInfo.value.original_filename || 'archive')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}
async function removeArchive() {
  if (!archiveRow.value) return
  try {
    await ElMessageBox.confirm('确认删除该仪器的档案文件？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteInstrumentArchive(archiveRow.value.id)
    ElMessage.success('已删除')
    await loadArchiveInfo(archiveRow.value.id)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}
async function previewArchive() {
  if (!archiveRow.value || !archiveInfo.value.has_archive) return
  const ext = (archiveInfo.value.file_ext || '').toLowerCase()
  const fname = archiveInfo.value.original_filename || '档案预览'
  // PDF：浏览器内置阅读器可直接渲染
  if (ext === '.pdf') {
    try {
      const blob = await downloadInstrumentArchive(archiveRow.value.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) {
      ElMessage.error('预览失败')
    }
    return
  }
  // docx（含已由 .doc 转换而来的）：前端 mammoth 转 HTML，在浏览器内显示（不下载，与文件管理一致）
  if (ext === '.docx') {
    previewVisible.value = true
    previewTitle.value = fname
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await downloadInstrumentArchive(archiveRow.value.id)
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // 其他格式（极少，如转换失败保留的 .doc）：回退下载
  try {
    const blob = await downloadInstrumentArchive(archiveRow.value.id)
    triggerDownload(blob, fname)
    ElMessage.info('该格式暂不支持在线预览，已为你下载文件')
  } catch (e) {
    ElMessage.error('预览失败')
  }
}
function triggerDownload(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name || 'archive'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ---------------- 批量导入 ----------------
const importVisible = ref(false)
const importPath = ref('E:\\生免组管理体系文件\\生免组仪器档案')
const importing = ref(false)
const importResult = ref(null)
async function doImport() {
  if (!importPath.value.trim()) {
    ElMessage.warning('请填写档案目录')
    return
  }
  importing.value = true
  importResult.value = null
  try {
    const res = await importArchivesFolder(importPath.value.trim())
    importResult.value = res
    ElMessage.success(`成功导入 ${res.imported} 个仪器档案`)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

function formatSize(n) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}
function formatTime(v) {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 19)
}
</script>

<style scoped>
.page {
  height: 100%;
}
.repair-meta {
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  padding: 8px 12px;
  margin-bottom: 10px;
  border-radius: 4px;
  font-size: 13px;
  color: #303133;
}
.repair-tip {
  background: #fafafa;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.8;
  color: #606266;
  margin-top: 10px;
}
.qr-tip {
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 10px;
}
.qr-url {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  word-break: break-all;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 6px 10px;
}
.repair-summary-count {
  margin-bottom: 10px;
  color: #606266;
  font-size: 13px;
}
.detail-text {
  white-space: pre-line;
  line-height: 1.7;
  word-break: break-all;
}
/* 仪器列表：允许单元格内容换行（最多两行），避免横向拖拉 */
.page :deep(.el-table .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
}
.page :deep(.el-table__row) td {
  padding-top: 8px;
  padding-bottom: 8px;
}
/* 对应项目数量统计 */
.linked-count {
  margin-top: 10px;
  padding: 8px 12px;
  text-align: right;
  font-size: 13px;
  color: #606266;
  background: #f5f7fa;
  border-radius: 4px;
}
.linked-count b {
  color: #409eff;
  font-size: 15px;
  padding: 0 2px;
}
/* 档案预览：复用的富文本样式 */
.doc-preview {
  max-height: 78vh;
  overflow: auto;
  padding: 8px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
  line-height: 1.7;
}
.doc-preview :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.doc-preview :deep(td),
.doc-preview :deep(th) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.doc-preview :deep(img) {
  max-width: 100%;
}
</style>
