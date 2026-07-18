<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <!-- ============ 月结 ============ -->
      <el-tab-pane label="室内质控月结" name="summary" v-if="auth.canAccessMenu('qc-monthly')">
        <div class="toolbar">
          <el-date-picker
            v-model="monthValue"
            type="month"
            placeholder="选择年月"
            format="YYYY-MM"
            value-format="YYYY-MM"
            @change="loadSummary"
            style="width: 160px"
          />
          <el-select
            v-model="filterInstrumentId"
            placeholder="按仪器筛选"
            style="width: 240px"
            @change="loadSummary"
          >
            <el-option label="全部仪器" :value="0" />
            <el-option
              v-for="opt in instrumentList"
              :key="opt.id"
              :label="instLabel(opt)"
              :value="opt.id"
            />
          </el-select>
          <el-select
            v-model="uploadInstrumentId"
            placeholder="先选择质控仪器"
            style="width: 240px"
          >
            <el-option
              v-for="opt in instrumentList"
              :key="opt.id"
              :label="instLabel(opt)"
              :value="opt.id"
            />
          </el-select>
          <el-button v-if="auth.canWrite('qc')" type="primary" @click="triggerCsv">上传该仪器 LIS 数据(CSV/XLSX)</el-button>
          <input ref="csvInput" type="file" accept=".csv,.xlsx,.xls" hidden @change="onCsvChange" />
          <el-button :disabled="!monthValue" @click="onExport">
            导出 CZ-012 月小结{{ filterInstrumentId ? '（本仪器）' : '' }}(Excel)
          </el-button>
          <span class="hint">
            月结按「每一台仪器」分块；上传前先在下拉中选好受控仪器（绑定仪器台账），系统按每日测值跑 Westgard 判失控并自动草拟文字小结；质控图 PDF 在每行「查看」中上传存档。
          </span>
        </div>

        <div v-if="!summaryRows.length && !loadingSummary" class="empty-tip">
          请选择年月后加载，或先选「质控仪器」再点击「上传 LIS 数据」导入本月质控。
        </div>

        <div v-for="g in groups" :key="g.key" class="inst-block">
          <div class="inst-title">
            <span class="inst-name">
              仪器：{{ g.instrument || '未指定' }}
              <template v-if="g.model">（{{ g.model }}）</template>
              <template v-if="g.deptNo">（编号：{{ g.deptNo }}）</template>
            </span>
            <span class="inst-count">{{ g.rows.length }} 项</span>
          </div>
          <el-table :data="g.rows" v-loading="loadingSummary" border stripe>
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="daily-wrap">
                  <div class="daily-head">
                    <strong>每日测值（失控点已标红）</strong>
                    <el-upload
                      :show-file-list="false"
                      :before-upload="(f) => onPdfUpload(row, f)"
                      accept=".pdf"
                    >
                      <el-button v-if="auth.canWrite('qc')" size="small" type="primary" plain>上传质控图PDF</el-button>
                    </el-upload>
                    <el-button
                      v-if="row.pdf_filename"
                      size="small"
                      type="success"
                      plain
                      @click="previewPdf(row)"
                    >预览质控图</el-button>
                    <el-button
                      v-if="row.pdf_filename"
                      size="small"
                      type="danger"
                      plain
                      @click="removePdf(row)"
                    >删除质控图</el-button>
                  </div>
                  <el-table :data="row._daily" size="small" border>
                    <el-table-column prop="qc_date" label="日期" width="120" />
                    <el-table-column prop="value" label="测定值" width="110" />
                    <el-table-column label="状态" width="160">
                      <template #default="d">
                        <el-tag v-if="d.row.is_out_of_control" type="danger" size="small">
                          失控 {{ d.row.rule_violated }}
                        </el-tag>
                        <el-tag v-else type="success" size="small">在控</el-tag>
                      </template>
                    </el-table-column>
                  </el-table>
                  <div class="note-box">
                    <div class="note-label">失控处理说明：</div>
                    <el-input
                      v-model="row.handling_note"
                      type="textarea"
                      :rows="2"
                      placeholder="如：X月X日水平2失控，因质控品复溶不当，重做后恢复在控。"
                      @blur="saveNote(row)"
                    />
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="test_item" label="项目" width="160" />
            <el-table-column prop="lot_no" label="质控批号" width="110" />
            <el-table-column prop="unit" label="单位" width="70" />
            <el-table-column prop="level" label="水平" width="70" />
            <el-table-column prop="target_mean" label="靶值" width="90" />
            <el-table-column prop="target_sd" label="靶值SD" width="80" />
            <el-table-column label="靶值CV%" width="90">
              <template #default="{ row }">{{ fmtPct(row.target_cv) }}</template>
            </el-table-column>
            <el-table-column prop="mean" label="均值" width="90" />
            <el-table-column prop="sd" label="SD" width="80" />
            <el-table-column label="CV%" width="90">
              <template #default="{ row }">{{ fmtPct(row.cv) }}</template>
            </el-table-column>
            <el-table-column prop="n" label="n" width="55" />
            <el-table-column label="失控数" width="80">
              <template #default="{ row }">
                <span :class="{ danger: row.out_of_control_count > 0 }">{{ row.out_of_control_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="在控率" width="90">
              <template #default="{ row }">{{ fmtPct(row.in_control_rate * 100) }}</template>
            </el-table-column>
            <el-table-column prop="quality_goal" label="质量目标" width="120" />
            <el-table-column prop="operator" label="操作人" width="160" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button v-if="auth.canWrite('qc')" size="small" type="danger" plain @click="delSummary(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 文字部分（CZ-012 月小结） -->
          <div v-if="reportMap[g.key]" class="report-box">
            <div class="report-title">文字部分（CZ-012 月小结）</div>
            <el-form label-position="top" class="report-form">
              <el-form-item label="一、仪器运行情况">
                <el-input v-model="reportMap[g.key].operation_status" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item label="二、各项目是否出现漂移或趋势性改变">
                <el-input v-model="reportMap[g.key].drift_trend" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="三、各项目CV%设置是否达标">
                <el-input v-model="reportMap[g.key].cv_setting_ok" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="四、各项目计算CV%是否达标">
                <el-input v-model="reportMap[g.key].cv_calc_ok" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="五、各项目质控频次是否达标">
                <el-input v-model="reportMap[g.key].freq_ok" type="textarea" :rows="3" />
              </el-form-item>
            </el-form>
            <el-button type="primary" size="small" :loading="reportMap[g.key]._saving" @click="saveReport(g)">
              保存总结文字
            </el-button>
            <el-button size="small" @click="openDocxPreview(g)">预览月小结</el-button>
            <el-button type="success" size="small" :loading="reportMap[g.key]._docxing" @click="downloadDocx(g)">
              下载 Word (A4 横向)
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- ============ 室间质评 ============ -->
      <el-tab-pane label="室间质评" name="eqa" v-if="auth.canAccessMenu('eqa')">
        <div class="toolbar">
          <el-date-picker
            v-model="eqaYear"
            type="year"
            placeholder="选择年度"
            value-format="YYYY"
            @change="loadEqa"
            style="width: 140px"
          />
          <el-select v-model="eqaOrg" placeholder="机构" clearable @change="loadEqa" style="width: 130px">
            <el-option label="全部机构" value="" />
            <el-option label="卫健委" value="卫健委" />
            <el-option label="北京市" value="北京市" />
          </el-select>
          <el-select v-model="eqaGroup" placeholder="专业组" clearable @change="loadEqa" style="width: 130px">
            <el-option label="全部专业组" value="" />
            <el-option label="生化" value="生化" />
            <el-option label="免疫" value="免疫" />
            <el-option label="凝血" value="凝血" />
            <el-option label="其他" value="其他" />
          </el-select>
          <el-button v-if="auth.canWrite('eqa')" type="primary" @click="onAddPlan">新增质评计划</el-button>
          <el-button :disabled="!eqaYear" :loading="copyingPrev" @click="onCopyAllPrev">一键复制上一年</el-button>
          <el-button :disabled="!eqaYear" @click="onExportEqa">导出{{ eqaYear || '' }}计划(Excel)</el-button>
          <el-tag v-if="pendingScoreCount > 0" type="warning" size="small" style="margin-left:6px">成绩待填 {{ pendingScoreCount }} 条</el-tag>
          <span class="hint">
            年度计划按机构/专业组/轮次管理；在卫健委/临检中心网页上报后，请在此标记「已上报」；上报截止前30天自动在首页提醒中心预警；结果回报后回填成绩并可在行内「导入报告」。
          </span>
        </div>

        <!-- 检测提醒仅在工作台显示，此处不再展示（按需求移除） -->

        <!-- 年度计划表 -->
        <el-table
          class="eqa-table"
          :data="eqaRowsView"
          v-loading="loadingEqa"
          border
          stripe
          :default-sort="{ prop: 'returned', order: 'ascending' }"
          @sort-change="onEqaSortChange"
        >
          <el-table-column prop="org" label="组织机构" width="132" sortable="custom" />
          <el-table-column label="专业组" width="74">
            <template #default="{ row }">
              <el-tag size="small" :type="groupTagType(row.group)">{{ row.group || '其他' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="program" label="项目组" width="100" />
          <el-table-column prop="item" label="细项" min-width="110" show-overflow-tooltip />
          <el-table-column prop="round_no" label="轮次" width="62" />
          <el-table-column prop="sample_date" label="检测日期" width="108" sortable="custom" />
          <el-table-column prop="due_date" label="上报截止日期" width="110" sortable="custom" />
          <el-table-column label="已上报" width="74" prop="returned" sortable="custom">
            <template #default="{ row }">
              <el-tag :type="row.returned ? 'success' : 'info'" size="small">{{ row.returned ? '已上报' : '未上报' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="成绩" width="144" show-overflow-tooltip />
          <el-table-column label="合格" width="74">
            <template #default="{ row }">
              <span v-if="row.result || row.score">
                <el-tag v-if="/^成绩不适用|^不适用|^不评价/.test(row.result || '')" type="info" size="small">不评价</el-tag>
                <el-tag v-else :type="row.qualified ? 'success' : 'danger'" size="small">{{ row.qualified ? '合格' : '不合格' }}</el-tag>
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="报告" width="94">
            <template #default="{ row }">
              <template v-if="row.report_file">
                <el-button size="small" type="success" link @click="onDownloadReport(row)">已导入</el-button>
                <el-tag v-if="!row.result && !row.score" type="warning" size="small" effect="plain" class="pending-tag">成绩待填</el-tag>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="NCCL编码" width="100">
            <template #default="{ row }">
              <span v-if="row.org === '卫健委'">{{ extractNccl(row.note) || '—' }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="176" fixed="right">
            <template #default="{ row }">
              <div class="op-cell">
                <el-button size="small" type="warning" plain @click="openResultDialog(row)">录入结果</el-button>
                <el-button size="small" :type="row.returned ? 'info' : 'warning'" plain @click="onReturn(row)">已上报</el-button>
                <el-button size="small" type="success" plain @click="openImportDialog(row)">导入报告</el-button>
                <el-button size="small" type="success" plain :disabled="!row.report_file" @click="onPreviewReport(row)">预览回报</el-button>
                <el-button v-if="auth.canWrite('eqa')" size="small" type="primary" plain @click="onEditPlan(row)">编辑</el-button>
                <el-button v-if="auth.canWrite('eqa')" size="small" type="danger" plain @click="onDelPlan(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 半年/年度总结（生化+凝血、免疫 两组分别出报告，各自负责人签字） -->
        <div class="eqa-summary">
          <div class="report-title">半年/年度总结（质评部门 × 专业组，分别出报告）</div>
          <div class="toolbar" style="margin-bottom:8px">
            <el-radio-group v-model="summaryDept" @change="loadSummaryStat">
              <el-radio-button label="卫健委">国家卫健委临检中心</el-radio-button>
              <el-radio-button label="北京市">北京市临检中心</el-radio-button>
            </el-radio-group>
            <el-radio-group v-model="summaryCategory" @change="loadSummaryStat">
              <el-radio-button label="生化+凝血" />
              <el-radio-button label="免疫" />
            </el-radio-group>
            <el-select v-model="summaryHalf" style="width:170px" @change="loadSummaryStat">
              <el-option label="上半年（1-6月）" :value="1" />
              <el-option label="下半年（7-12月）" :value="2" />
              <el-option label="全年" :value="0" />
            </el-select>
            <el-button :loading="loadingSummaryStat" @click="loadSummaryStat">统计</el-button>
            <el-button type="primary" :loading="generatingSummary" @click="saveAndGenerate">
              保存并生成报告(Word)
            </el-button>
            <el-button :disabled="!summaryDocUrl" @click="summaryPreview = true">预览</el-button>
            <el-button :disabled="!summaryDocUrl" type="success" @click="exportSummaryDoc">导出Word</el-button>
            <span v-if="summaryGeneratedAt" class="gen-tip">已生成：{{ summaryGeneratedAt }}</span>
          </div>

          <div v-if="summaryStat" class="summary-cats">
            <div class="cat-block" v-for="c in summaryStat.categories" :key="c.category">
              <div class="cat-head">{{ c.category }}</div>
              <span>项目组 <b>{{ c.programs }}</b></span>
              <span>细项 <b>{{ c.items_total }}</b></span>
              <span>合格 <b>{{ c.qualified }}</b></span>
              <span>不合格 <b>{{ c.unqualified }}</b></span>
              <span>不评价 <b>{{ c.not_evaluated }}</b></span>
              <span>细项合格率 <b>{{ c.qualify_rate != null ? c.qualify_rate + '%' : '—' }}</b></span>
            </div>
            <div class="cat-block total" v-if="summaryStat.total && summaryStat.categories.length > 1">
              <div class="cat-head">合计</div>
              <span>项目组 <b>{{ summaryStat.total.programs }}</b></span>
              <span>细项 <b>{{ summaryStat.total.items_total }}</b></span>
              <span>合格 <b>{{ summaryStat.total.qualified }}</b></span>
              <span>不合格 <b>{{ summaryStat.total.unqualified }}</b></span>
              <span>不评价 <b>{{ summaryStat.total.not_evaluated }}</b></span>
              <span>细项合格率 <b>{{ summaryStat.total.qualify_rate != null ? summaryStat.total.qualify_rate + '%' : '—' }}</b></span>
            </div>
          </div>

          <el-input
            v-model="summaryText"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 24 }"
            placeholder="合格项目分析 / 总结叙述（保存后写入总结报告 Word）"
            style="margin-top:8px"
          />

          <!-- 结果报告合并打印：按当前 年份/部门/半年，合并该专业组已导入的全部报告为一 PDF -->
          <div class="merge-print" style="margin-top:10px">
            <span class="merge-label">结果报告合并打印：</span>
            <el-button :loading="mergingReport" @click="mergePrint('生化+凝血')">生化+凝血</el-button>
            <el-button :loading="mergingReport" @click="mergePrint('免疫')">免疫</el-button>
            <span class="merge-tip">（按当前年份 / 质评部门 / 半年 筛选，合并所选专业组已导入的全部报告为一 PDF，在新标签打开后可直接打印）</span>
          </div>
        </div>

        <!-- 新增/编辑计划对话框 -->
        <el-dialog v-model="planDialog" :title="planEditingId ? '编辑质评计划' : '新增质评计划'" width="560px">
          <el-form :model="planForm" label-width="120px">
            <div class="form-group-title">一、上报信息</div>
            <el-form-item label="复制上一年" v-if="!planEditingId">
              <el-select v-model="copyPrevId" placeholder="选择上一年计划以快速填充（机构/项目组/细项/轮次）" filterable style="width:100%" @change="onCopyPrev">
                <el-option v-for="p in prevYearPlans" :key="p.id" :label="`${p.org}｜${p.program}｜${p.item}｜${p.round_no}`" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="年度"><el-input v-model="planForm.year" placeholder="如 2026" /></el-form-item>
            <el-form-item label="组织机构"><el-input v-model="planForm.org" placeholder="如 北京市临床检验中心" /></el-form-item>
            <el-form-item label="专业组">
              <el-select v-model="planForm.group" placeholder="选择专业组" style="width:100%">
                <el-option label="生化" value="生化" />
                <el-option label="免疫" value="免疫" />
                <el-option label="凝血" value="凝血" />
                <el-option label="其他" value="其他" />
              </el-select>
            </el-form-item>
            <el-form-item label="项目组"><el-input v-model="planForm.program" placeholder="如 常规化学A / 肝纤 / 药物监测" /></el-form-item>
            <el-form-item label="细项"><el-input v-model="planForm.item" placeholder="如 葡萄糖 / 具体检测项目" /></el-form-item>
            <el-form-item label="轮次"><el-input v-model="planForm.round_no" placeholder="如 第1次 / 2026-1" /></el-form-item>
            <el-form-item label="样本检测日期"><el-date-picker v-model="planForm.sample_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="上报截止日期"><el-date-picker v-model="planForm.due_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
            <el-form-item label="是否上报">
              <el-switch v-model="planForm.returned" active-text="已上报" inactive-text="未上报" />
            </el-form-item>
            <el-form-item label="上报备注"><el-input v-model="planForm.note" type="textarea" :rows="2" placeholder="上报相关备注（如上报批次号）" /></el-form-item>

            <div class="form-group-title">二、结果回报</div>
            <el-form-item label="成绩"><el-input v-model="planForm.result" placeholder="如 合格/PT及格" /></el-form-item>
            <el-form-item label="是否合格"><el-switch v-model="planForm.qualified" /></el-form-item>
            <el-form-item label="得分"><el-input v-model="planForm.score" placeholder="如 95 / 100" /></el-form-item>
            <el-form-item v-if="planForm.report_file" label="已导入报告">
              <el-button type="success" link @click="onDownloadReport({ id: planEditingId, report_file: planForm.report_file })">点击下载</el-button>
              <el-button type="danger" link @click="onDeleteReportInline">移除</el-button>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="planDialog = false">取消</el-button>
            <el-button type="primary" :loading="planSaving" @click="savePlan">保存</el-button>
          </template>
        </el-dialog>
        <!-- 导入质评报告并回填成绩/合格对话框 -->
        <el-dialog v-model="importDialog" title="导入质评报告并回填成绩" width="500px" append-to-body :close-on-click-modal="false">
          <el-form label-width="92px">
            <el-form-item label="PDF 报告" required>
              <input type="file" accept="application/pdf" @change="onImportFileChange" />
              <div v-if="importFile" class="file-tip">已选：{{ importFile.name }}</div>
              <div v-else class="file-tip muted">请选择卫健委/北京市下发的成绩 PDF</div>
            </el-form-item>
            <el-form-item label="成绩/结果">
              <el-input v-model="importForm.result" placeholder="如 合格 / PT及格 / 优秀" />
            </el-form-item>
            <el-form-item label="得分">
              <el-input v-model="importForm.score" placeholder="如 95 / 100 / 良好" />
            </el-form-item>
            <el-form-item label="是否合格">
              <el-switch v-model="importForm.qualified" active-text="合格" inactive-text="不合格" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="importDialog = false">取消</el-button>
            <el-button type="primary" :loading="importSaving" @click="submitImportReport">导入并记录</el-button>
          </template>
        </el-dialog>

        <!-- 质评报告预览对话框 -->
        <el-dialog v-model="previewDialog" title="质评报告预览" width="82%" top="5vh" @close="onPreviewClose">
          <div v-loading="previewLoading" element-loading-text="报告加载中…" style="height: 76vh">
            <iframe v-if="previewUrl" :src="previewUrl" style="width: 100%; height: 100%; border: none"></iframe>
            <el-empty v-else description="正在加载报告…" />
          </div>
        </el-dialog>

        <!-- 总结报告预览（HTML 渲染，与 Word 一致） -->
        <el-dialog v-model="summaryPreview" title="总结报告预览" width="80%" top="5vh">
          <div class="eqa-summary-preview" v-if="summaryStat">
            <h2 class="prev-title">生化免疫组室间质评总结报告表</h2>
            <p class="prev-meta">年份：{{ eqaYear }}年（{{ periodLabel }}）&nbsp;&nbsp;质评部门：{{ summaryDeptName }}（{{ summaryCategory }}组）</p>

            <h3>一、按专业分类统计</h3>
            <table class="prev-table">
              <tr><th>分类</th><th>项目组数</th><th>细项数</th><th>合格</th><th>不合格</th><th>不评价</th><th>细项合格率</th></tr>
              <tr v-for="c in summaryStat.categories" :key="c.category">
                <td>{{ c.category }}</td><td>{{ c.programs }}</td><td>{{ c.items_total }}</td>
                <td>{{ c.qualified }}</td><td>{{ c.unqualified }}</td><td>{{ c.not_evaluated }}</td>
                <td>{{ c.qualify_rate != null ? c.qualify_rate + '%' : '—' }}</td>
              </tr>
              <tr class="prev-total" v-if="summaryStat.categories.length > 1">
                <td>合计</td><td>{{ summaryStat.total.programs }}</td><td>{{ summaryStat.total.items_total }}</td>
                <td>{{ summaryStat.total.qualified }}</td><td>{{ summaryStat.total.unqualified }}</td><td>{{ summaryStat.total.not_evaluated }}</td>
                <td>{{ summaryStat.total.qualify_rate != null ? summaryStat.total.qualify_rate + '%' : '—' }}</td>
              </tr>
            </table>

            <h3>二、不合格项目</h3>
            <table class="prev-table" v-if="unqItems.length">
              <tr><th>分类</th><th>测定项目</th><th>上报结果</th><th>预期结果/允许范围</th><th>原因分析及纠正措施</th></tr>
              <tr v-for="(it, i) in unqItems" :key="i">
                <td>{{ it.category }}</td><td>{{ it.item }}</td><td>{{ it.result || it.score }}</td>
                <td>见官方成绩报告允许范围</td><td>（待填）</td>
              </tr>
            </table>
            <p v-else>本统计期内无不合格项目。</p>

            <h3>三、不评价项目（单列，不计不合格）</h3>
            <table class="prev-table" v-if="neItems.length">
              <tr><th>分类</th><th>测定项目</th><th>备注</th></tr>
              <tr v-for="(it, i) in neItems" :key="i">
                <td>{{ it.category }}</td><td>{{ it.item }}</td><td>{{ it.result || '不予评价' }}</td>
              </tr>
            </table>
            <p v-else>无。</p>

            <h3>四、合格项目分析</h3>
            <p>{{ passLine }}</p>
            <p v-if="summaryText && summaryText.trim()" class="prev-narr">{{ summaryText }}</p>

            <h3>五、签字与审核</h3>
            <p>填表人：______________&nbsp;&nbsp;填报日期：______年____月____日</p>
            <p>审核意见：________________________________________</p>
            <p>审核人：______________&nbsp;&nbsp;日期：______年____月____日</p>
            <p>生化免疫组员工签字：______________________________</p>
          </div>
        </el-dialog>

        <!-- CZ-012 月小结预览（HTML，与 Word 版一致） -->
        <el-dialog v-model="docxPreview" title="月小结预览（与 Word 版一致）" width="92%" top="3vh">
          <div class="docx-preview" v-if="docxGroup">
            <h2 class="prev-title">{{ docxYear }}年{{ String(docxMonth).padStart(2, '0') }}月　仪器：{{ docxInst }}</h2>
            <table class="prev-table">
              <tr>
                <th>项目</th><th>质控批号</th><th>单位</th><th>水平</th><th>靶值</th><th>靶值SD</th>
                <th>靶值CV%</th><th>均值</th><th>SD</th><th>CV%</th><th>n</th><th>失控数</th><th>在控率</th><th>质量目标</th>
              </tr>
              <tr v-for="r in docxGroup.rows" :key="r.id">
                <td>{{ r.test_item }}</td><td>{{ r.lot_no }}</td><td>{{ r.unit }}</td><td>{{ r.level }}</td>
                <td>{{ fmtNum(r.target_mean) }}</td><td>{{ fmtNum(r.target_sd) }}</td><td>{{ r.target_cv?.toFixed(2) }}%</td>
                <td>{{ fmtNum(r.mean) }}</td><td>{{ fmtNum(r.sd) }}</td><td>{{ r.cv?.toFixed(2) }}%</td>
                <td>{{ r.n }}</td><td>{{ r.out_of_control_count }}</td><td>{{ (r.in_control_rate * 100).toFixed(1) }}%</td><td>{{ r.quality_goal }}</td>
              </tr>
            </table>
            <h3>文字部分</h3>
            <p><b>一、仪器运行情况：</b>{{ (docxReport.operation_status || '（未填写）') }}</p>
            <p><b>二、各项目是否出现漂移或趋势性改变：</b>{{ (docxReport.drift_trend || '（未填写）') }}</p>
            <p><b>三、各项目CV%设置是否达标：</b>{{ (docxReport.cv_setting_ok || '（未填写）') }}</p>
            <p><b>四、各项目计算CV%是否达标：</b>{{ (docxReport.cv_calc_ok || '（未填写）') }}</p>
            <p><b>五、各项目质控频次是否达标：</b>{{ (docxReport.freq_ok || '（未填写）') }}</p>
            <div class="prev-foot">
              <el-button type="success" :loading="docxDownloading" @click="downloadDocx(docxGroup)">下载 Word (A4 横向打印)</el-button>
            </div>
          </div>
        </el-dialog>

        <!-- 录入结果（样本×项目矩阵 + 双人签字审核单打印） -->
        <el-dialog
          v-model="resultDialog"
          :title="`录入结果 - ${resultPlan?.org || ''} ${resultPlan?.program || ''} ${resultPlan?.round_no || ''}`"
          width="94%" top="3vh"
          append-to-body
          @close="onResultClose"
        >
          <div class="result-entry">
            <el-alert type="info" :closable="false" show-icon
              title="按样本×项目填写实测结果；项目与单位自动取自计划与项目查询库（可改）。需换算上报的项目（如雌二醇、孕酮等）会自动显示「原值→上报值」两栏，原值输入即自动换算。定性试验（肝炎/感染血清学）按 COI 自动判阴阳性（P=阳性/N=阴性）：常规项目 COI>1 判阳；HBeAb、HBcAb 例外（COI<1 判阳）；COI 值照填，阴阳性实时算出并随结果保存。"
              style="margin-bottom:10px" />
            <!-- 样本 / 项目 定义 -->
            <div class="re-def">
              <div class="re-def-col">
                <div class="re-label">样本编号（每行一个）</div>
                <el-input v-model="sampleText" type="textarea" :rows="3" placeholder="如 202511" />
              </div>
              <div class="re-def-col">
                <div class="re-label">检测项目（每行一个）</div>
                <el-input v-model="itemText" type="textarea" :rows="3" placeholder="如 TSH / T4 / 雌二醇" />
              </div>
              <div class="re-def-col">
                <div class="re-label">单位（每行对应项目，自动取自项目库，可改）</div>
                <el-input v-model="unitText" type="textarea" :rows="3" placeholder="如 mIU/L / ng/mL（留空则无）" />
              </div>
              <div class="re-def-col re-def-btns">
                <el-button @click="applyGrid">生成/刷新表格</el-button>
                <el-button @click="addRow">+ 增加样本行</el-button>
                <el-button @click="addCol">+ 增加项目列</el-button>
              </div>
            </div>
            <!-- 矩阵表 -->
            <el-table :data="gridRows" border class="re-grid" size="small">
              <el-table-column label="样本编号" width="140">
                <template #default="{ row }">
                  <el-input v-model="row.sample" placeholder="样本编号" />
                </template>
              </el-table-column>
              <el-table-column v-for="it in gridItems" :key="it.key" :label="it.name + (it.unit ? ' (' + it.unit + ')' : '') + (it.qualitative ? ' ·COI' : '')" min-width="150">
                <template #default="{ row }">
                  <template v-if="it.conv">
                    <div class="conv-cell">
                      <el-input v-model="row.values[it.key]" size="small"
                        :placeholder="'原值(' + it.conv.from + ')'" @input="onConvInput(row, it)" />
                      <span class="conv-arrow">×{{ it.conv.factor }}→</span>
                      <el-input v-model="row.report[it.key]" size="small"
                        :placeholder="'上报(' + it.conv.to + ')'" />
                    </div>
                  </template>
                  <template v-else-if="it.qualitative">
                    <div class="qual-cell">
                      <el-input v-model="row.values[it.key]" size="small" placeholder="COI值"
                        @input="onQualInput(row, it)" />
                      <span class="pn-badge" :class="pnClass(qualPN(row, it))">{{ qualPN(row, it) || '—' }}</span>
                    </div>
                  </template>
                  <el-input v-else v-model="row.values[it.key]" placeholder="结果" />
                </template>
              </el-table-column>
            </el-table>
            <!-- 打印元信息 -->
            <div class="re-meta">
              <div class="re-meta-item">
                <span>测定人</span>
                <el-input v-model="meta.tester" placeholder="测定人" />
              </div>
              <div class="re-meta-item">
                <span>审核人</span>
                <el-input v-model="meta.reviewer" placeholder="审核人" />
              </div>
              <div class="re-meta-item">
                <span>测定日期</span>
                <el-date-picker v-model="meta.test_date" type="date" value-format="YYYY-MM-DD" placeholder="测定日期" style="width:100%" />
              </div>
              <div class="re-meta-item">
                <span>回报日期</span>
                <el-date-picker v-model="meta.return_date" type="date" value-format="YYYY-MM-DD" placeholder="回报日期" style="width:100%" />
              </div>
            </div>
            <div v-if="resultPlan && resultPlan.note" class="sys-note">
              <span class="sys-note-label">系统自动说明：</span>{{ resultPlan.note }}
            </div>
            <el-input v-model="meta.note" type="textarea" :rows="2" placeholder="备注（人工填写，打印用，如上报注意事项、单位说明等）" style="margin-top:8px" />
          </div>
          <template #footer>
            <el-button @click="resultDialog = false">关闭</el-button>
            <el-button :loading="exporting" @click="exportExcel">导出Excel</el-button>
            <el-button :loading="resultSaving" @click="printResult">打印（双人签字审核）</el-button>
            <el-button type="primary" :loading="resultSaving" @click="saveResult">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
      <el-tab-pane label="仪器间比对" name="cmp" lazy v-if="auth.canAccessMenu('comparison')">
        <Comparison />
      </el-tab-pane>
      <el-tab-pane label="室间比对" name="interlab" lazy v-if="auth.canAccessMenu('interlab')">
        <InterlabComparison />
      </el-tab-pane>
      <el-tab-pane label="质控品换批号累靶" name="lot" lazy v-if="auth.canAccessMenu('qc-target')">
        <TargetValueBoard />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ExcelJS from 'exceljs'
import {
  listQCSummaries, uploadQCSummary, getQCDaily, updateQCSummary, deleteQCSummary,
  uploadQCPdf, downloadQCPdf, deleteQCPdf, exportQCSummary,
  getQCReport, upsertQCReport, exportQCReportDocx,
} from '../../api/qc'
import { getQCInstruments } from '../../api/qc'
import {
  listEqaPlans, createEqaPlan, updateEqaPlan, deleteEqaPlan, copyPrevYearEqa,
  getEqaAlerts, getEqaSummary, getEqaSummaryText, upsertEqaSummaryText, exportEqaPlans,
  uploadEqaReport, downloadEqaReport, deleteEqaReport,
  getEqaResult, saveEqaResult,
  getEqaSummaryByCategory, generateEqaSummary, eqaSummaryDocUrl, mergeEqaReports,
} from '../../api/eqa'
import { useAuthStore } from '../../store/auth'
import Comparison from '../comparison/Comparison.vue'
import InterlabComparison from '../interlab/InterlabComparison.vue'
import TargetValueBoard from './TargetValueBoard.vue'

const activeTab = ref('summary')
const auth = useAuthStore()

// 按权限收口可见页签：technical_support 仅见其被授权的页签
const visibleTabs = computed(() => {
  const map = {
    summary: 'qc-monthly',
    eqa: 'eqa',
    cmp: 'comparison',
    interlab: 'interlab',
    lot: 'qc-target',
  }
  return Object.keys(map).filter((t) => auth.canAccessMenu(map[t]))
})
// 当前选中页签不可见时，自动切到第一个可见页签（如 technical_support 默认落在"仪器间比对"）
watch(
  visibleTabs,
  (v) => {
    if (v.length && !v.includes(activeTab.value)) activeTab.value = v[0]
  },
  { immediate: true },
)

// ---------- 仪器台账（仅室内质控受控仪器） ----------
const instrumentList = ref([])
async function loadInstruments() {
  try {
    const res = await getQCInstruments()
    instrumentList.value = res || []
  } catch (e) {
    instrumentList.value = []
  }
}

// 下拉选项标签：名称（型号｜编号），型号缺失时仅显示编号
function instLabel(opt) {
  const parts = []
  if (opt.model) parts.push(opt.model)
  if (opt.dept_no) parts.push(opt.dept_no)
  return opt.name + (parts.length ? `（${parts.join('｜')}）` : '')
}

// ---------- 月结 ----------
const monthValue = ref('')
const summaryRows = ref([])
const loadingSummary = ref(false)
const filterInstrumentId = ref(0)      // 0 = 全部
const uploadInstrumentId = ref(null)   // 上传时选定的受控仪器
const csvInput = ref(null)
const reportMap = reactive({})         // blockKey -> 文字报告对象

// CZ-012 月小结预览 / Word 下载
const docxPreview = ref(false)
const docxGroup = ref(null)
const docxDownloading = ref(false)
const docxYear = computed(() => { const { year } = parseMonth(); return year || '—' })
const docxMonth = computed(() => { const { month } = parseMonth(); return month || 0 })
const docxInst = computed(() => {
  const g = docxGroup.value
  if (!g) return ''
  return g.instrument || '—' + (g.deptNo ? '（编号：' + g.deptNo + '）' : '')
})
const docxReport = computed(() => (docxGroup.value ? (reportMap[docxGroup.value.key] || {}) : {}))
function openDocxPreview(g) {
  docxGroup.value = g
  docxPreview.value = true
}
async function downloadDocx(g) {
  const grp = g || docxGroup.value
  if (!grp) return
  const { year, month } = parseMonth()
  const rep = reportMap[grp.key]
  if (rep) rep._docxing = true
  docxDownloading.value = true
  try {
    const blob = await exportQCReportDocx(year, month, grp.rows[0]?.instrument_id || undefined)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const instId = grp.rows[0]?.instrument_id
    a.download = `室内质控月小结_${year}年${String(month).padStart(2, '0')}月${instId ? '_' + instId : ''}.docx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('Word 月小结已生成')
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    if (rep) rep._docxing = false
    docxDownloading.value = false
  }
}
function fmtNum(v) {
  if (v === null || v === undefined || v === '') return '-'
  return Number(v).toFixed(4)
}

// 按仪器分块（受控：优先用 instrument_id 作为块键）；显示仪器编号
const groups = computed(() => {
  const map = {}
  for (const r of summaryRows.value) {
    const key = r.instrument_id ? String(r.instrument_id) : (r.instrument || '未知')
    if (!map[key]) {
      const inst = r.instrument_id ? instrumentList.value.find((i) => i.id === r.instrument_id) : null
      map[key] = {
        instrument: r.instrument,
        deptNo: r.instrument_no,
        model: inst?.model || '',
        key,
        rows: [],
      }
    }
    map[key].rows.push(r)
  }
  return Object.keys(map)
    .sort((a, b) => (map[a].instrument || '').localeCompare(map[b].instrument || '', 'zh'))
    .map((k) => map[k])
})

function parseMonth() {
  if (!monthValue.value) return { year: null, month: null }
  const [y, m] = monthValue.value.split('-').map(Number)
  return { year: y, month: m }
}
function fmtPct(v) {
  if (v === null || v === undefined || v === '') return '-'
  return Number(v).toFixed(2) + '%'
}

async function loadSummary() {
  const { year, month } = parseMonth()
  loadingSummary.value = true
  try {
    const params = {}
    if (year) params.year = year
    if (month) params.month = month
    if (filterInstrumentId.value) params.instrument_id = filterInstrumentId.value
    params.page_size = 500
    const res = await listQCSummaries(params)
    const rows = (res.items || []).map((it) => ({ ...it, _daily: [] }))
    summaryRows.value = rows
    // 懒加载每日测值
    await Promise.all(rows.map(async (r) => {
      try { r._daily = await getQCDaily(r.id) } catch (e) { r._daily = [] }
    }))
    // 载入各仪器块的文字报告
    const seen = new Set()
    for (const r of rows) {
      const key = r.instrument_id ? String(r.instrument_id) : (r.instrument || '未知')
      if (seen.has(key)) continue
      seen.add(key)
      try {
        const rep = await getQCReport(r.instrument_id || null, year, month)
        reportMap[key] = rep
      } catch (e) { /* 暂无报告 */ }
    }
  } finally {
    loadingSummary.value = false
  }
}
watch(activeTab, (t) => { if (t === 'summary' && !summaryRows.value.length && monthValue.value) loadSummary() })
onMounted(loadInstruments)

function triggerCsv() { csvInput.value?.click() }
async function onCsvChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!uploadInstrumentId.value) {
    ElMessage.warning('请先在上方「质控仪器」下拉中选好仪器，再上传该仪器的 LIS 数据')
    e.target.value = ''
    return
  }
  try {
    const res = await uploadQCSummary(file, uploadInstrumentId.value)
    ElMessage.success(`上传成功：新增 ${res.created} 条，更新 ${res.updated} 条`)
    if (res.items && res.items.length) {
      const it = res.items[0]
      const newMonth = `${it.year}-${String(it.month).padStart(2, '0')}`
      if (newMonth !== monthValue.value) monthValue.value = newMonth
      else await loadSummary()
    }
  } catch (err) {
    ElMessage.error('上传失败：' + (err.response?.data?.detail || err.message))
  } finally {
    e.target.value = ''
  }
}
async function onExport() {
  const { year, month } = parseMonth()
  try {
    const blob = await exportQCSummary(year, month, filterInstrumentId.value || undefined)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `室内质控月小结_${year || 'ALL'}_${month || 'ALL'}${filterInstrumentId.value ? '_' + filterInstrumentId.value : ''}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error('导出失败：' + (err.response?.data?.detail || err.message))
  }
}
async function saveNote(row) {
  try {
    await updateQCSummary(row.id, { handling_note: row.handling_note || '' })
  } catch (e) { ElMessage.error('保存说明失败') }
}
async function onPdfUpload(row, file) {
  try {
    const res = await uploadQCPdf(row.id, file)
    row.pdf_path = res.pdf_path
    row.pdf_filename = res.pdf_filename
    ElMessage.success('质控图已上传')
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  }
  return false
}
async function previewPdf(row) {
  try {
    const blob = await downloadQCPdf(row.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) {
    ElMessage.error('预览失败：' + (e.response?.data?.detail || e.message))
  }
}
async function removePdf(row) {
  await ElMessageBox.confirm('确认删除该质控图？', '提示', { type: 'warning' })
  await deleteQCPdf(row.id)
  row.pdf_path = ''
  row.pdf_filename = ''
  ElMessage.success('已删除')
}
async function delSummary(row) {
  await ElMessageBox.confirm(`确认删除「${row.instrument || ''} / ${row.test_item} ${row.level}」月结记录？`, '提示', { type: 'warning' })
  await deleteQCSummary(row.id)
  ElMessage.success('已删除')
  await loadSummary()
}
async function saveReport(g) {
  const rep = reportMap[g.key]
  if (!rep) return
  rep._saving = true
  try {
    const { year, month } = parseMonth()
    await upsertQCReport({
      instrument_id: g.rows[0].instrument_id || null,
      instrument: g.instrument || '',
      instrument_no: g.rows[0].instrument_no || '',
      year, month,
      operation_status: rep.operation_status || '',
      drift_trend: rep.drift_trend || '',
      cv_setting_ok: rep.cv_setting_ok || '',
      cv_calc_ok: rep.cv_calc_ok || '',
      freq_ok: rep.freq_ok || '',
    })
    ElMessage.success('总结文字已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    rep._saving = false
  }
}

// ---------- 室间质评（EQA） ----------
const eqaYear = ref(String(new Date().getFullYear()))
const eqaOrg = ref('')
const eqaRows = ref([])
const eqaGroup = ref('')
const loadingEqa = ref(false)
const eqaAlerts = ref([])
// 按所选机构过滤后的提醒（全部机构时显示全部）
const eqaAlertsView = computed(() =>
  eqaOrg.value ? eqaAlerts.value.filter((a) => a.org === eqaOrg.value) : eqaAlerts.value
)
const planDialog = ref(false)
const planEditingId = ref(null)
const planSaving = ref(false)
// 复制上一年：上一年计划列表 + 当前选中的源计划 id
const prevYearPlans = ref([])
const copyPrevId = ref(null)
// 一键复制上一年（批量）按钮 loading 态
const copyingPrev = ref(false)
const planForm = reactive({
  year: '', org: '', program: '', group: '', item: '', round_no: '',
  sample_date: '', due_date: '', returned: false,
  result: '', qualified: false, score: '', note: '',
  report_file: '',
})
// 导入报告对话框（选 PDF + 回填成绩/合格）
const importDialog = ref(false)
const importTargetId = ref(null)
const importFile = ref(null)
const importForm = reactive({ result: '', score: '', qualified: false })
const importSaving = ref(false)
// 报告预览
const previewDialog = ref(false)
const previewUrl = ref('')
const previewLoading = ref(false)
// 录入结果（样本×项目矩阵）
const resultDialog = ref(false)
const resultPlan = ref(null)
const resultTargetId = ref(null)
const resultSaving = ref(false)
const exporting = ref(false)
const sampleText = ref('')
const itemText = ref('')
const unitText = ref('')         // 与项目逐行对应，可手动编辑；默认来自项目查询库
const gridItems = ref([])        // [{key, name, unit}]
const gridRows = ref([])         // [{sample, values:{key:val}}]
const meta = reactive({ tester: '', reviewer: '', test_date: '', return_date: '', note: '' })
const summaryHalf = ref(1)          // 1=上半年，2=下半年，0=全年
const summaryCategory = ref('生化+凝血')  // 分类：生化+凝血 / 免疫（两组分别出报告）
const summaryDept = ref('卫健委')    // 质评部门（org）：卫健委 / 北京市（按部门分别出报告）
// 质评部门显示名映射
const DEPT_OPTIONS = [
  { value: '卫健委', label: '国家卫健委临检中心' },
  { value: '北京市', label: '北京市临检中心' },
]
function deptDisplayName(v) {
  return DEPT_OPTIONS.find(d => d.value === v)?.label || v || ''
}
const summaryDeptName = computed(() => deptDisplayName(summaryDept.value))
const summaryStat = ref(null)
const loadingSummaryStat = ref(false)
const summaryText = ref('')
const savingSummary = ref(false)
const generatingSummary = ref(false)
const mergingReport = ref(false)
const summaryDocUrl = ref('')
const summaryGeneratedAt = ref('')
const summaryPreview = ref(false)

// 预览用派生数据
const periodLabel = computed(() => ({ 1: '上半年（1-6月）', 2: '下半年（7-12月）', 0: '全年' }[summaryHalf.value] || '全年'))
const unqItems = computed(() => {
  const out = []
  for (const c of summaryStat.value?.categories || []) {
    for (const it of c.unqualified_list || []) out.push({ category: c.category, ...it })
  }
  return out
})
const neItems = computed(() => {
  const out = []
  for (const c of summaryStat.value?.categories || []) {
    for (const it of c.not_evaluated_list || []) out.push({ category: c.category, ...it })
  }
  return out
})
const passLine = computed(() => {
  const t = summaryStat.value?.total
  if (!t) return ''
  const rate = t.qualify_rate != null ? t.qualify_rate + '%' : '—'
  return `${eqaYear.value}年室间质评（${summaryDeptName.value}${summaryCategory.value}）细项合格率 ${rate} （合格 ${t.qualified} / 评价 ${t.items_evaluated} 项）。`
})

// 合格项目分析「模版」：文字为空时自动预填（含动态数字与四个分析段落）
function buildSummaryTemplate() {
  const s = summaryStat.value
  if (!s) return ''
  const c = (s.categories && s.categories[0]) || s.total || {}
  const prog = c.programs ?? 0
  const items = c.items_total ?? 0
  const ev = c.items_evaluated ?? 0
  const q = c.qualified ?? 0
  const u = c.unqualified ?? 0
  const ne = c.not_evaluated ?? 0
  const rate = c.qualify_rate != null ? c.qualify_rate + '%' : '—'
  return `一、总体评价
${eqaYear.value}年（${periodLabel.value}）${summaryDeptName.value}${summaryCategory.value}组室间质评细项合格率${rate}，共参加计划${prog}项、检测细项${items}项（已按名称去重），合格${q}项、不合格${u}项、不评价${ne}项。
（可简述整体水平、与往年对比等。）

二、不合格/不评价项目分析
（如有不合格或不评价项目，逐条说明：测定项目、偏离原因、已采取的纠正措施及效果验证；如无则写"本统计期无不合格/不评价项目。"）

三、薄弱环节与持续改进
（结合室内质控、人员操作、试剂与校准品、检测系统等方面，分析可能存在的风险与改进方向。）

四、下一步工作打算
（下阶段重点改进措施与计划。）`
}

function groupTagType(g) {
  return g === '生化' ? 'warning' : g === '免疫' ? 'success' : g === '凝血' ? 'danger' : 'info'
}
// 从备注中提取卫健委 NCCL 计划编码（如 NCCL-C-01）
function extractNccl(note) {
  if (!note) return ''
  const m = String(note).match(/NCCL-[A-Z]+-[0-9]+/)
  return m ? m[0] : ''
}

async function loadEqa() {
  if (!eqaYear.value) { eqaRows.value = []; return }
  loadingEqa.value = true
  try {
    const params = { year: Number(eqaYear.value), page_size: 500 }
    if (eqaOrg.value) params.org = eqaOrg.value
    if (eqaGroup.value) params.group = eqaGroup.value
    const res = await listEqaPlans(params)
    eqaRows.value = res.items || []
  } finally {
    loadingEqa.value = false
  }
  // 检测提醒仅在工作台展示，室间质评 tab 不再加载/显示提醒
}

// 排序：已上报的始终排到最后（主排序），用户点击的列作为次级排序
const eqaSortState = ref({ prop: 'returned', order: 'ascending' })
function onEqaSortChange({ prop, order }) {
  eqaSortState.value = { prop, order }
}
const eqaRowsView = computed(() => {
  const rows = [...(eqaRows.value || [])]
  const { prop, order } = eqaSortState.value
  const dir = order === 'descending' ? -1 : order === 'ascending' ? 1 : 0
  return rows.sort((a, b) => {
    // 主排序：未上报在前，已上报在后
    if (a.returned !== b.returned) return a.returned ? 1 : -1
    // 次级排序：用户所选列
    if (dir !== 0 && prop) {
      let av = a[prop]
      let bv = b[prop]
      if (av == null) av = ''
      if (bv == null) bv = ''
      if (av < bv) return -1 * dir
      if (av > bv) return 1 * dir
    }
    return 0
  })
})
const pendingScoreCount = computed(() => {
  // 成绩待填：已导入报告 PDF，但成绩/得分均未回填
  return (eqaRows.value || []).filter(r => r.report_file && !r.result && !r.score).length
})
async function loadAlerts() {
  try {
    eqaAlerts.value = await getEqaAlerts()
  } catch (e) {
    eqaAlerts.value = []
  }
}
// 一键复制上一年全部计划到当前查看的年度（target=当前 eqaYear，source=target-1）
async function onCopyAllPrev() {
  if (!eqaYear.value) return
  const target = Number(eqaYear.value)
  const source = target - 1
  try {
    await ElMessageBox.confirm(
      `将把 ${source} 年的全部质评计划复制到 ${target} 年。` +
      `检测/截止日期会自动顺延 1 年；「是否上报/成绩/合格/得分/报告」字段清空；若 ${target} 年已存在相同（机构+项目组+细项+轮次）的计划则自动跳过。确定复制吗？`,
      '一键复制上一年',
      { type: 'warning', confirmButtonText: '确定复制', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  copyingPrev.value = true
  try {
    const res = await copyPrevYearEqa(target)
    ElMessage.success(`已复制 ${res.copied} 条，跳过 ${res.skipped} 条（${source} 年共 ${res.copied + res.skipped} 条）`)
    await loadEqa()
  } catch (e) {
    ElMessage.error('复制失败：' + (e?.response?.data?.detail || e?.message || e))
  } finally {
    copyingPrev.value = false
  }
}

function onAddPlan() {
  Object.assign(planForm, {
    year: eqaYear.value, org: '', program: '', group: '', item: '', round_no: '',
    sample_date: '', due_date: '', returned: false,
    result: '', qualified: false, score: '', note: '', report_file: '',
  })
  copyPrevId.value = null
  planEditingId.value = null
  planDialog.value = true
  // 载入上一年计划，供「复制上一年」快速填充
  try {
    listEqaPlans({ year: Number(eqaYear.value) - 1, page_size: 500 }).then((prev) => {
      prevYearPlans.value = prev.items || []
    }).catch(() => { prevYearPlans.value = [] })
  } catch (e) {
    prevYearPlans.value = []
  }
}
// 把 YYYY-MM-DD 类日期的年份整体 +delta（如 2025-03-19 -> 2026-03-19）
function addYear(d, delta) {
  if (!d) return d
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d)
  if (!m) return d
  return `${parseInt(m[1], 10) + delta}-${m[2]}-${m[3]}`
}
// 从上年计划快速填充（year 改当前年；检测/截止日期年份 +1；回报/报告清空，避免带入旧结果）
function onCopyPrev(id) {
  const p = prevYearPlans.value.find((x) => x.id === id)
  if (!p) return
  const dy = Number(eqaYear.value) - Number(p.year || eqaYear.value)
  Object.assign(planForm, {
    year: eqaYear.value,
    org: p.org || '',
    program: p.program || '',
    group: p.group || '',
    item: p.item || '',
    round_no: p.round_no || '',
    sample_date: addYear(p.sample_date, dy),
    due_date: addYear(p.due_date, dy),
    returned: false,
    result: '',
    qualified: false,
    score: '',
    note: p.note || '',
    report_file: '',
  })
  ElMessage.success(`已复制上一年「${p.org} ${p.program} ${p.item} ${p.round_no}」，检测/截止日期已顺延 ${dy} 年，请核对后保存`)
}
function onEditPlan(row) {
  Object.assign(planForm, {
    year: String(row.year), org: row.org, program: row.program, group: row.group || '', item: row.item,
    round_no: row.round_no, sample_date: row.sample_date, due_date: row.due_date,
    returned: !!row.returned, result: row.result, qualified: !!row.qualified,
    score: row.score, note: row.note, report_file: row.report_file || '',
  })
  planEditingId.value = row.id
  planDialog.value = true
}
async function onReturn(row) {
  try {
    await updateEqaPlan(row.id, { ...row, returned: true })
    ElMessage.success('已标记为已上报')
    await loadEqa()
    await loadAlerts()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}
// ---- 质评报告导入 / 下载 / 删除 ----
function openImportDialog(row) {
  importTargetId.value = row.id
  importFile.value = null
  importForm.result = row.result || ''
  importForm.score = row.score || ''
  importForm.qualified = !!row.qualified
  importDialog.value = true
}
function onImportFileChange(e) {
  const file = e.target.files && e.target.files[0]
  if (!file) { importFile.value = null; return }
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.error('仅支持 PDF 质评报告')
    e.target.value = ''
    importFile.value = null
    return
  }
  importFile.value = file
}
async function submitImportReport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择 PDF 报告文件')
    return
  }
  const id = importTargetId.value
  if (!id) return
  importSaving.value = true
  try {
    await uploadEqaReport(id, importFile.value, {
      result: importForm.result,
      score: importForm.score,
      qualified: importForm.qualified,
    })
    ElMessage.success('报告已导入，成绩与合格情况已记录')
    importDialog.value = false
    await loadEqa()
  } catch (err) {
    ElMessage.error('导入失败：' + (err.response?.data?.detail || err.message))
  } finally {
    importSaving.value = false
  }
}
async function onDownloadReport(row) {
  try {
    const blob = await downloadEqaReport(row.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `质评报告_${row.id}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error('下载失败：' + (err.response?.data?.detail || err.message))
  }
}
async function onPreviewReport(row) {
  previewLoading.value = true
  previewDialog.value = true
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
  try {
    const blob = await downloadEqaReport(row.id)
    previewUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    ElMessage.error('预览失败：' + (err.response?.data?.detail || err.message))
    previewDialog.value = false
  } finally {
    previewLoading.value = false
  }
}
function onPreviewClose() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

// ---------------- 录入结果（样本×项目矩阵 + 双人签字审核单） ----------------
// EQA 上报单位换算表（与后端 eqa.py::EQA_UNIT_CONVERSIONS 保持一致）
const EQA_CONV = [
  { names: ['游离雌三醇', '雌三醇', 'ue3'], factor: 3.467, from: 'pg/mL', to: 'nmol/L' },
  { names: ['雌二醇', 'e2'], factor: 3.67, from: 'pg/mL', to: 'pmol/L' },
  { names: ['孕酮', '黄体酮', 'p'], factor: 3.18, from: 'ng/mL', to: 'nmol/L' },
  { names: ['pth', '甲状旁腺激素'], factor: 0.106, from: 'pg/mL', to: 'pmol/L' },
  { names: ['皮质醇', 'cortisol'], factor: 27.64, from: 'μg/dL', to: 'nmol/L' },
  { names: ['acth'], factor: 0.2202, from: 'pg/mL', to: 'pmol/L' },
  { names: ['醛固酮', 'aldosterone', 'ald'], factor: 2.775, from: 'pg/mL', to: 'nmol/L' },
  { names: ['胰岛素', 'insulin'], factor: 6.965, from: 'μU/mL', to: 'pmol/L' },
  { names: ['c肽', 'c-peptide', '连接肽'], factor: 0.333, from: 'ng/mL', to: 'nmol/L' },
  { names: ['vd', '25-ohvd', '维生素d', '25羟维生素d'], factor: 2.494, from: 'ng/mL', to: 'nmol/L' },
  { names: ['肾素', 'renin'], factor: 1.2, from: 'ng/mL', to: 'uIU/mL' },
]
function _convNorm(s) {
  return (s || '').replace(/\s/g, '').toLowerCase()
}
function matchConv(name) {
  const nn = _convNorm(name)
  if (!nn) return null
  for (const r of EQA_CONV) {
    if (r.names.includes(nn)) return r
    for (const a of r.names) if (a.length >= 2 && nn.includes(a)) return r
  }
  return null
}
function _roundNum(x, d = 4) {
  const f = Math.pow(10, d)
  return Number(Math.round(x * f) / f)
}

// EQA 定性试验（COI）阴阳性判定（与后端 eqa.py 保持一致）
// program 含「肝炎/感染」→ 定性试验；HBeAb/HBcAb 反向（COI<1 判阳）。
const QUAL_PROGRAM_KEYWORDS = ['肝炎', '感染']
const QUAL_REVERSE_ITEMS = [
  'hbeab', '抗-hbe', '抗hbe', 'e抗体', '乙肝e抗体',
  'hbcab', '抗-hbc', '抗hbc', '核心抗体', '乙肝核心抗体',
]
function _qualNorm(s) {
  return (s || '').replace(/[\s（）()]/g, '').toLowerCase()
}
function isQualitativeProgram(p) {
  const pp = (p || '').toLowerCase()
  return QUAL_PROGRAM_KEYWORDS.some((k) => pp.includes(k))
}
function isReverseItem(item) {
  const nn = _qualNorm(item)
  if (!nn) return false
  return QUAL_REVERSE_ITEMS.some((k) => {
    const kk = _qualNorm(k)
    return kk === nn || kk.includes(nn) || nn.includes(kk)
  })
}
function computePN(value, reverse) {
  let s = String(value == null ? '' : value).trim()
  s = s.replace(/\/[PN]$/i, '').trim() // 去掉末尾 /P /N（兼容旧数据）
  if (!s) return ''
  const below = /^(<|≤|<=|小于)/.test(s)
  s = s.replace(/^(<|≤|<=|小于)/, '').trim()
  const v = parseFloat(s)
  if (isNaN(v)) return ''
  if (below) return reverse ? 'P' : 'N' // 低于 cutoff：常规判阴、反向(HBeAb/HBcAb)判阳
  return reverse ? (v < 1 ? 'P' : 'N') : (v > 1 ? 'P' : 'N')
}

async function openResultDialog(row) {
  resultTargetId.value = row.id
  resultPlan.value = row
  try {
    const res = await getEqaResult(row.id)
    const rd = res.result_data || {}
    const samples = (rd.samples && rd.samples.length) ? rd.samples : []
    const items = (rd.items && rd.items.length) ? rd.items : []
    const units = rd.units || {}
    const conv = rd.conv || {}
    const oldCells = rd.cells || {}
    const oldReport = rd.cells_report || {}
    sampleText.value = samples.join('\n')
    itemText.value = items.join('\n')
    unitText.value = items.map((n) => units[n] || '').join('\n')
    gridItems.value = items.map((n) => ({
      key: n, name: n, unit: units[n] || '', conv: conv[n] || null,
      qualitative: isQualitativeProgram(resultPlan.value?.program),
      reverse: isReverseItem(n),
    }))
    gridRows.value = samples.map((s) => {
      const prev = oldCells[s] || {}
      const prevR = oldReport[s] || {}
      const values = {}
      const report = {}
      for (const it of items) {
        values[it] = prev[it] || ''
        report[it] = prevR[it] || ''
      }
      return { sample: s, values, report }
    })
    const sysNote = (row && row.note) || ''
    const savedNote = (rd.meta && rd.meta.note) || ''
    // 历史防护：若已存备注与系统自动说明雷同，视为系统内容，不回填人工备注框
    const looksSystem = sysNote && savedNote && savedNote.replace(/\s/g, '').includes(sysNote.replace(/\s/g, '').slice(0, 6))
    Object.assign(meta, {
      tester: (rd.meta && rd.meta.tester) || '',
      reviewer: (rd.meta && rd.meta.reviewer) || '',
      test_date: (rd.meta && rd.meta.test_date) || (row.sample_date || ''),
      return_date: (rd.meta && rd.meta.return_date) || (row.due_date || ''),
      note: looksSystem ? '' : savedNote,
    })
    resultDialog.value = true
  } catch (err) {
    ElMessage.error('加载失败：' + (err.response?.data?.detail || err.message))
  }
}
function applyGrid() {
  const samples = sampleText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  const items = [...new Set(itemText.value.split('\n').map((s) => s.trim()).filter(Boolean))]
  const unitLines = unitText.value.split('\n').map((s) => s.trim())
  // 保留已有值（按样本名 + 项目名匹配）
  const old = {}
  for (const r of gridRows.value) old[r.sample] = { values: r.values || {}, report: r.report || {} }
  gridItems.value = items.map((n, i) => {
    const c = matchConv(n)
    const unit = c ? c.to : (unitLines[i] || '')
    return { key: n, name: n, unit, conv: c, qualitative: isQualitativeProgram(resultPlan.value?.program), reverse: isReverseItem(n) }
  })
  gridRows.value = samples.map((s) => {
    const prev = old[s] || { values: {}, report: {} }
    const values = {}
    const report = {}
    for (const it of items) {
      values[it] = prev.values[it] || ''
      report[it] = prev.report[it] || ''
    }
    return { sample: s, values, report }
  })
}
function onConvInput(row, it) {
  if (!it.conv) return
  const num = parseFloat(row.values[it.key])
  if (!isNaN(num)) {
    row.report[it.key] = String(_roundNum(num * it.conv.factor))
  } else {
    row.report[it.key] = ''
  }
}
function onQualInput(row, it) {
  // 定性试验：COI 值变化触发响应式，P/N 由 qualPN 实时计算（无需额外处理）
}
function qualPN(row, it) {
  const v = row.values ? row.values[it.key] : ''
  return computePN(v, it.reverse)
}
function pnClass(pn) {
  return pn === 'P' ? 'pn-pos' : (pn === 'N' ? 'pn-neg' : 'pn-none')
}
function addRow() {
  gridRows.value.push({
    sample: '',
    values: Object.fromEntries(gridItems.value.map((it) => [it.key, ''])),
    report: Object.fromEntries(gridItems.value.map((it) => [it.key, ''])),
  })
}
function addCol() {
  const name = '新项目' + (gridItems.value.length + 1)
  const c = matchConv(name)
  gridItems.value.push({ key: name, name, unit: c ? c.to : '', conv: c, qualitative: isQualitativeProgram(resultPlan.value?.program), reverse: isReverseItem(name) })
  for (const r of gridRows.value) {
    if (!(name in r.values)) r.values[name] = ''
    if (!(name in r.report)) r.report[name] = ''
  }
}
function onResultClose() {
  resultTargetId.value = null
  resultPlan.value = null
}
async function saveResult() {
  if (!resultTargetId.value) return
  applyGrid()
  const payload = {
    samples: gridRows.value.map((r) => r.sample),
    items: gridItems.value.map((it) => it.name),
    units: Object.fromEntries(gridItems.value.map((it) => [it.name, it.conv ? it.conv.to : (it.unit || '')])),
    conv: Object.fromEntries(gridItems.value.filter((it) => it.conv).map((it) => [it.name, it.conv])),
    cells: Object.fromEntries(gridRows.value.map((r) => [r.sample, { ...r.values }])),
    cells_report: Object.fromEntries(gridRows.value.map((r) => [r.sample, { ...r.report }])),
    meta: { ...meta },
  }
  resultSaving.value = true
  try {
    await saveEqaResult(resultTargetId.value, payload)
    ElMessage.success('结果已保存')
  } catch (err) {
    ElMessage.error('保存失败：' + (err.response?.data?.detail || err.message))
  } finally {
    resultSaving.value = false
  }
}
function buildPrintHtml() {
  const plan = resultPlan.value || {}
  const allItems = gridItems.value
  const rows = gridRows.value
  // 项目过多（>10）→ 上下两行：项目分两半，各一张整页宽表格上下叠放，列宽翻倍、字放大
  const useTwoRow = allItems.length > 10

  const buildHead = (items) =>
    '<th>样本编号</th>' + items.map((it) => {
      const unit = it.unit ? ` (${escapeHtml(it.unit)})` : ''
      return `<th>${escapeHtml(it.name)}${unit}</th>`
    }).join('')

  const buildBody = (items) =>
    rows.map((r) => {
      const tds = items.map((it) => {
        let main, sub = ''
        if (it.conv) {
          main = r.report[it.key] || ''
          const orig = r.values[it.key]
          if (orig) sub = `原 ${escapeHtml(orig)} ${escapeHtml(it.conv.from)}`
        } else if (it.qualitative) {
          main = r.values[it.key] || ''
          const pn = computePN(r.values[it.key], it.reverse)
          if (pn) sub = `判定：${pn === 'P' ? '阳性' : '阴性'}`
        } else {
          main = r.values[it.key] || ''
        }
        return `<td>${escapeHtml(main)}${sub ? `<div class="orig">${sub}</div>` : ''}</td>`
      }).join('')
      return `<tr><td>${escapeHtml(r.sample)}</td>${tds}</tr>`
    }).join('')

  let tableHtml
  if (useTwoRow) {
    const mid = Math.ceil(allItems.length / 2)
    const top = allItems.slice(0, mid)
    const bottom = allItems.slice(mid)
    const tbl = (items, label) =>
      `<div class="tbl-block"><div class="tbl-cap">${label}</div><table><thead><tr>${buildHead(items)}</tr></thead><tbody>${buildBody(items)}</tbody></table></div>`
    tableHtml = `${tbl(top, '（一）')}${tbl(bottom, '（二）')}`
  } else {
    tableHtml = `<table><thead><tr>${buildHead(allItems)}</tr></thead><tbody>${buildBody(allItems)}</tbody></table>`
  }

  const title = `${escapeHtml(plan.org || '')} ${escapeHtml(plan.program || '')} ${escapeHtml(plan.round_no || '')} 室间质评结果记录`
  return `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>${title}</title>
<style>
  /* 打印基础样式 */
  body{font-family:"Microsoft YaHei","SimSun",serif;padding:24px;color:#000}
  h2{text-align:center;margin:0 0 4px;font-size:18px}
  .sub{text-align:center;color:#444;font-size:12px;margin-bottom:10px}
  table{border-collapse:collapse;width:100%;font-size:11px;table-layout:fixed}
  th,td{border:1px solid #000;padding:4px 3px;text-align:center;word-break:break-all}
  th{background:#f0f0f0;font-size:10.5px}
  .orig{font-size:9.5px;color:#666;margin-top:1px}
  .meta{display:flex;flex-wrap:wrap;gap:18px;font-size:12px;margin:10px 0}
  /* 签字区——一行排开，年月日留足手写空位 */
  .sign{margin-top:28px;display:flex;align-items:flex-end;font-size:14px;white-space:nowrap}
  .sign-item{display:inline-flex;flex-direction:column;align-items:center}
  .sign-item.tester,.sign-item.reviewer{flex:0 0 auto;margin-right:6%}
  .sign-item.date{flex:1 1 auto;text-align:right}
  .sign-item .line{border-top:1px solid #000;margin-top:6px;padding-top:2px;min-height:28px;display:flex;align-items:flex-end;justify-content:center}
  .sign-item.date .line{justify-content:flex-end;padding-right:4px;gap:8px}
  .sign-item.date .line span{display:inline-block;width:36px;text-align:center;border-bottom:1px solid #999;line-height:20px}
  /* 分页控制 */
  thead{display:table-header-group}
  tbody tr{break-inside:avoid;page-break-inside:avoid}
  .sign{break-inside:avoid;page-break-inside:avoid}
  /* 项目多：上下两行叠放，每张整页宽、项目减半、列宽翻倍、字放大 */
  .two-row table{font-size:13px}
  .two-row table th{font-size:12px}
  .two-row table .orig{font-size:10px}
  .tbl-block{margin-bottom:14px}
  .tbl-cap{font-size:13px;font-weight:bold;margin:6px 0 4px}
  .sys-note-print{margin:10px 0 2px;font-size:11px;color:#555;border:1px dashed #bbb;padding:4px 8px;background:#fafafa}
  @media print{
    body{padding:0}
    @page{size:A4 landscape;margin:8mm 10mm}
    th,td{padding:3px 2px;font-size:9.5px}
    th{font-size:9px}
    .orig{font-size:8.5px}
    .two-row table{font-size:11px}
    .two-row table th{font-size:10px}
    .two-row table .orig{font-size:9px}
  }
</style></head>
<body>
  <h2>${title}</h2>
  <div class="sub">年度：${escapeHtml(String(plan.year || ''))} ｜ 测定日期：${escapeHtml(meta.test_date || '')} ｜ 回报日期：${escapeHtml(meta.return_date || '')}</div>
  <div class="${useTwoRow ? 'two-row' : ''}">${tableHtml}</div>
  <div class="meta">
    <span>测定人：${escapeHtml(meta.tester || '＿＿＿＿')}</span>
    <span>审核人：${escapeHtml(meta.reviewer || '＿＿＿＿')}</span>
    <span>备注：${escapeHtml(meta.note || '')}</span>
  </div>
  <div class="sign">
    <div class="sign-item tester"><span>测定人（签字）</span><div class="line">&nbsp;</div></div>
    <div class="sign-item reviewer"><span>审核人（签字）</span><div class="line">&nbsp;</div></div>
    <div class="sign-item date"><span>日期：</span><div class="line"><span>　年</span><span>　月</span><span>　日</span></div></div>
  </div>
</body></html>`
}
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}
function printResult() {
  applyGrid()
  const html = buildPrintHtml()
  const w = window.open('', '_blank')
  if (!w) {
    ElMessage.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    return
  }
  w.document.open()
  w.document.write(html)
  w.document.close()
  setTimeout(() => { w.focus(); w.print() }, 300)
}
async function exportExcel() {
  try {
    exporting.value = true
    applyGrid()
    const plan = resultPlan.value || {}
    const items = gridItems.value
    const rows = gridRows.value
    const title = `${plan.org || ''} ${plan.program || ''} ${plan.round_no || ''} 室间质评结果记录`
    // 项目过多（>10）→ 上下两行：两组共用同一列区域，每张表整页宽、项目减半、列宽翻倍、字放大
    const useTwoRow = items.length > 10
    let groups
    if (useTwoRow) {
      const mid = Math.ceil(items.length / 2)
      groups = [items.slice(0, mid), items.slice(mid)]
    } else {
      groups = [items]
    }
    const sheetCols = groups[0].length + 1

    const wb = new ExcelJS.Workbook()
    wb.creator = '生免速查工具'
    wb.views = [{ x: 0, y: 0, firstSheet: 0, activeTab: 0, visibility: 'visible' }]
    const ws = wb.addWorksheet('质评结果', { views: [{ state: 'visible' }] })

    // 标题（合并居中）
    ws.mergeCells(1, 1, 1, sheetCols)
    const tCell = ws.getCell(1, 1)
    tCell.value = title
    tCell.font = { bold: true, size: 14 }
    tCell.alignment = { horizontal: 'center', vertical: 'middle' }
    ws.getRow(1).height = 22

    // 副标题
    ws.mergeCells(2, 1, 2, sheetCols)
    const sCell = ws.getCell(2, 1)
    sCell.value = `年度：${plan.year || ''} ｜ 测定日期：${meta.test_date || ''} ｜ 回报日期：${meta.return_date || ''} ｜ 测定人：${meta.tester || ''} ｜ 审核人：${meta.reviewer || ''}`
    sCell.font = { size: 10, color: { argb: 'FF444444' } }
    sCell.alignment = { horizontal: 'center', vertical: 'middle' }

    const thin = { style: 'thin' }
    const styleCell = (cell, isHeader) => {
      cell.border = { top: thin, left: thin, bottom: thin, right: thin }
      cell.alignment = { horizontal: 'center', vertical: 'center', wrapText: true }
      if (isHeader) {
        cell.font = { bold: true }
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF0F0F0' } }
      }
    }

    // 逐组写表（每组上下叠放，共用列区域 → fitToWidth 让每张表占满页宽）
    let r = 3
    for (let gi = 0; gi < groups.length; gi++) {
      const gItems = groups[gi]
      const gCols = gItems.length + 1
      const headerRow = r
      ws.getCell(headerRow, 1).value = '样本编号'
      gItems.forEach((it, i) => {
        const c = ws.getCell(headerRow, i + 2)
        c.value = it.unit ? `${it.name} (${it.unit})` : it.name
      })
      for (let c = 1; c <= gCols; c++) styleCell(ws.getCell(headerRow, c), true)
      ws.getRow(headerRow).height = 28
      r = headerRow + 1
      rows.forEach((row) => {
        ws.getCell(r, 1).value = row.sample
        gItems.forEach((it, i) => {
          let main, sub = ''
          if (it.conv) {
            main = row.report[it.key] || ''
            const orig = row.values[it.key]
            if (orig) sub = `原 ${orig} ${it.conv.from}`
          } else if (it.qualitative) {
            main = row.values[it.key] || ''
            const pn = computePN(row.values[it.key], it.reverse)
            if (pn) sub = pn === 'P' ? '阳性' : '阴性'
          } else {
            main = row.values[it.key] || ''
          }
          const c = ws.getCell(r, i + 2)
          c.value = main + (sub ? `\n${sub}` : '')
        })
        for (let c = 1; c <= gCols; c++) styleCell(ws.getCell(r, c), false)
        r++
      })
      r += 2 // 两组之间空两行
    }

    // 系统自动说明（来自计划级 note，单独成行，不与人工备注混淆）
    if (plan.note) {
      ws.getCell(r, 1).value = '系统自动说明：' + plan.note + '（本行为系统生成，非人工备注）'
      ws.getCell(r, 1).font = { size: 10, italic: true, color: { argb: 'FF666666' } }
      r++
    }
    // 签字区（一行：测定人 / 审核人 / 日期 年 月 日）
    const signRow = r
    ws.getCell(signRow, 1).value = '测定人（签字）：'
    const testEnd = Math.max(3, Math.floor(sheetCols * 0.16))
    ws.mergeCells(signRow, 2, signRow, testEnd)
    ws.getCell(signRow, 2).border = { bottom: thin }
    const mid = Math.max(testEnd + 1, Math.floor(sheetCols * 0.5))
    ws.getCell(signRow, mid).value = '审核人（签字）：'
    ws.mergeCells(signRow, mid + 1, signRow, mid + 2)
    ws.getCell(signRow, mid + 1).border = { bottom: thin }
    const dCol = Math.max(mid + 3, sheetCols - 3)
    ws.getCell(signRow, dCol).value = '日期：'
    if (dCol + 1 <= sheetCols) {
      ws.getCell(signRow, dCol + 1).value = '年'
      ws.getCell(signRow, dCol + 1).border = { bottom: thin }
    }
    if (dCol + 2 <= sheetCols) {
      ws.getCell(signRow, dCol + 2).value = '月'
      ws.getCell(signRow, dCol + 2).border = { bottom: thin }
    }
    if (dCol + 3 <= sheetCols) {
      ws.getCell(signRow, dCol + 3).value = '日'
      ws.getCell(signRow, dCol + 3).border = { bottom: thin }
    }
    ws.getCell(signRow, 1).font = { size: 11 }
    ws.getCell(signRow, mid).font = { size: 11 }

    // 列宽（A4 横向 fitToWidth=1 会进一步压缩）
    ws.getColumn(1).width = 12
    groups[0].forEach((_, i) => { ws.getColumn(i + 2).width = Math.max(10, 16 - groups[0].length * 0.3) })

    // A4 打印设置
    ws.pageSetup = {
      paperSize: 9, // A4
      orientation: 'landscape',
      fitToPage: true,
      fitToWidth: 1,
      fitToHeight: 0,
      horizontalCentered: true,
      margins: { left: 0.3, right: 0.3, top: 0.4, bottom: 0.4, header: 0.2, footer: 0.2 },
    }
    // 仅单表时设表头重复（双表时每组都自带表头且通常在页内）
    if (!useTwoRow) ws.pageSetup.printTitlesRow = '3:3'

    const buf = await wb.xlsx.writeBuffer()
    const blob = new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.replace(/[\\/:*?"<>|]/g, '_')}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('已导出 Excel')
  } catch (err) {
    ElMessage.error('导出失败：' + (err.message || err))
  } finally {
    exporting.value = false
  }
}
async function onDeleteReportInline() {
  if (!planEditingId.value) return
  try {
    await deleteEqaReport(planEditingId.value)
    planForm.report_file = ''
    ElMessage.success('已移除报告')
    await loadEqa()
  } catch (err) {
    ElMessage.error('移除失败：' + (err.response?.data?.detail || err.message))
  }
}
async function onDelPlan(row) {
  await ElMessageBox.confirm(`确认删除「${row.org} ${row.program} ${row.round_no}」质评计划？`, '提示', { type: 'warning' })
  await deleteEqaPlan(row.id)
  ElMessage.success('已删除')
  await loadEqa()
  await loadAlerts()
}
async function savePlan() {
  planSaving.value = true
  try {
    const payload = { ...planForm, year: Number(planForm.year) || 0 }
    if (planEditingId.value) await updateEqaPlan(planEditingId.value, payload)
    else await createEqaPlan(payload)
    ElMessage.success('已保存')
    planDialog.value = false
    await loadEqa()
    await loadAlerts()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    planSaving.value = false
  }
}
async function loadSummaryStat() {
  if (!eqaYear.value) return
  loadingSummaryStat.value = true
  const cat = summaryCategory.value
  const dep = summaryDept.value
  try {
    summaryStat.value = await getEqaSummaryByCategory(Number(eqaYear.value), summaryHalf.value, cat, dep)
    try {
      const rep = await getEqaSummaryText(Number(eqaYear.value), summaryHalf.value, cat, dep)
      summaryText.value = rep.summary_text || ''
      if (!summaryText.value.trim()) {
        // 文字为空 → 预填「合格项目分析」模版（含动态数字）
        summaryText.value = buildSummaryTemplate()
      }
      if (rep.docx_path) {
        summaryDocUrl.value = eqaSummaryDocUrl(Number(eqaYear.value), summaryHalf.value, cat, dep)
        summaryGeneratedAt.value = rep.generated_at ? String(rep.generated_at).replace('T', ' ').slice(0, 19) : ''
      } else {
        summaryDocUrl.value = ''
        summaryGeneratedAt.value = ''
      }
    } catch (e) {
      summaryText.value = buildSummaryTemplate()
      summaryDocUrl.value = ''
      summaryGeneratedAt.value = ''
    }
  } finally {
    loadingSummaryStat.value = false
  }
}
// 保存某（部门×专业组）总结文字并生成 Word（自动存档）
async function saveAndGenerate() {
  if (!eqaYear.value) { ElMessage.warning('请先选择年度'); return }
  generatingSummary.value = true
  try {
    const res = await generateEqaSummary({
      year: Number(eqaYear.value),
      half: summaryHalf.value,
      department: summaryDept.value,
      category: summaryCategory.value,
      summary_text: summaryText.value,
    })
    summaryStat.value = res.stats
    summaryDocUrl.value = res.docx_url
    summaryGeneratedAt.value = res.generated_at ? String(res.generated_at).replace('T', ' ').slice(0, 19) : ''
    ElMessage.success('总结报告已生成并存档')
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    generatingSummary.value = false
  }
}
function exportSummaryDoc() {
  if (!summaryDocUrl.value) return
  window.open(summaryDocUrl.value, '_blank')
}
// 结果报告合并打印：合并该专业组已导入的全部报告为一 PDF，在新标签打开（可直接打印）
async function mergePrint(category) {
  if (mergingReport.value) return
  mergingReport.value = true
  try {
    const resp = await mergeEqaReports({
      year: Number(eqaYear.value),
      half: summaryHalf.value,
      category,
      department: summaryDept.value,
    })
    // 响应拦截器已把 response.data（Blob 本身）作为返回值，故 resp 即 Blob，不要再取 .data
    const blob = resp instanceof Blob ? resp : new Blob([resp], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (!win) {
      // 浏览器拦截弹窗时降级为下载
      const a = document.createElement('a')
      a.href = url
      a.download = `结果报告合并_${category}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
    }
    // 大 PDF（如卫健委合并可达数 MB）需足够时间加载，5 分钟后再释放 blob
    setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000)
  } catch (e) {
    let detail = ''
    const respData = e.response?.data
    try {
      if (respData instanceof Blob) {
        detail = (JSON.parse(await respData.text()).detail) || ''
      } else if (typeof respData === 'string') {
        detail = (JSON.parse(respData).detail) || ''
      }
    } catch (_) { /* ignore parse error */ }
    detail = detail || e.message || ''
    if (detail.includes('没有可合并')) {
      ElMessage.warning(`「${category}」在当前范围下没有可合并的已导入报告`)
    } else {
      ElMessage.error('合并打印失败：' + detail)
    }
  } finally {
    mergingReport.value = false
  }
}
async function onExportEqa() {
  if (!eqaYear.value) return
  try {
    const blob = await exportEqaPlans(Number(eqaYear.value), eqaOrg.value || undefined, eqaGroup.value || undefined)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `室间质评计划_${eqaYear.value}${eqaOrg.value ? '_' + eqaOrg.value : ''}${eqaGroup.value ? '_' + eqaGroup.value : ''}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error('导出失败：' + (err.response?.data?.detail || err.message))
  }
}
watch(activeTab, (t) => {
  if (t === 'eqa' && eqaYear.value) {
    loadEqa()
    loadAlerts()
    loadSummaryStat()
  }
})
</script>

<style scoped>
.page { height: 100%; }
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.toolbar .hint { color: #909399; font-size: 12px; flex: 1 1 100%; }
.empty-tip { color: #909399; font-size: 13px; padding: 24px 0; text-align: center; }
.inst-block { margin-bottom: 18px; }
.inst-title {
  display: flex; align-items: baseline; gap: 10px;
  padding: 6px 10px; margin-bottom: 6px;
  background: #f2f6fc; border-left: 4px solid #409eff; border-radius: 3px;
}
.inst-name { font-weight: 600; font-size: 14px; color: #303133; }
.inst-count { font-size: 12px; color: #909399; }
.daily-wrap { padding: 8px 16px; }
.daily-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.note-box { margin-top: 10px; }
.note-label { font-size: 13px; color: #606266; margin-bottom: 4px; }
.sys-note { margin-top: 8px; padding: 6px 10px; background: #f4f4f5; color: #909399; font-size: 12px; border-radius: 4px; line-height: 1.5; }
.sys-note-label { color: #c0c4cc; margin-right: 4px; }
.danger { color: #f56c6c; font-weight: 600; }
.report-box {
  margin-top: 10px; padding: 12px 14px;
  background: #fbfdff; border: 1px dashed #c6e2ff; border-radius: 6px;
}
.report-title { font-weight: 600; font-size: 13px; color: #409eff; margin-bottom: 8px; }
.report-form { margin-bottom: 6px; }
.report-form :deep(.el-form-item) { margin-bottom: 10px; }
.report-form :deep(.el-form-item__label) { font-size: 13px; color: #606266; padding-bottom: 2px; }
/* 室间质评 */
/* 行列间距调整：单元格内边距收紧、行高适中，按钮不挤 */
.eqa-table :deep(.el-table__cell) { padding: 6px 0; }
.eqa-table :deep(.cell) { padding: 0 10px; line-height: 1.45; }
.eqa-table :deep(.el-table__row) { height: 46px; }
.eqa-table :deep(.el-button) { margin: 2px 4px; }
.file-tip { margin-top: 6px; font-size: 12px; color: #606266; }
.file-tip.muted { color: #c0c4cc; }
.pending-tag { display: block; margin-top: 4px; width: fit-content; }
/* 操作列：窄列多行（2-3 行），文字完整不缩写 */
.eqa-table .op-cell { display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-start; align-items: center; }
.eqa-table .op-cell .el-button { margin: 2px; }
.eqa-alerts { margin: 12px 0; }
/* 结果报告合并打印 */
.merge-print { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.merge-print .merge-label { font-size: 13px; font-weight: 600; color: #303133; }
.merge-print .merge-tip { font-size: 12px; color: #909399; }
.eqa-alerts-title { font-weight: 600; font-size: 13px; color: #e6a23c; margin-bottom: 6px; }
.eqa-alerts .el-alert { margin-bottom: 6px; }
.form-group-title { font-weight: 600; color: #409eff; margin: 6px 0 10px; padding-left: 8px; border-left: 3px solid #409eff; }
.eqa-summary {
  margin-top: 18px; padding: 12px 14px;
  background: #fbfdff; border: 1px dashed #c6e2ff; border-radius: 6px;
}
.summary-stat { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; color: #606266; margin-bottom: 6px; }
.summary-stat b { color: #303133; }
.summary-cats { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 6px; }
.cat-block {
  flex: 1 1 280px; padding: 10px 12px; border: 1px solid #ebeef5; border-radius: 6px;
  background: #fff; display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; font-size: 13px; color: #606266;
}
.cat-block.total { background: #f0f7ff; border-color: #b3d8ff; font-weight: 600; }
.cat-head { width: 100%; font-weight: 700; color: #303133; font-size: 14px; border-bottom: 1px solid #f0f0f0; padding-bottom: 4px; }
.cat-block b { color: #303133; }
.gen-tip { font-size: 12px; color: #67c23a; align-self: center; }
.eqa-summary-preview { font-size: 13px; line-height: 1.8; color: #303133; }
.prev-title { text-align: center; font-size: 18px; margin: 4px 0 12px; }
.prev-meta { text-align: center; color: #606266; margin-bottom: 12px; }
.eqa-summary-preview h3 { font-size: 15px; margin: 16px 0 8px; border-left: 3px solid #409eff; padding-left: 8px; }
.prev-table { width: 100%; border-collapse: collapse; margin: 6px 0; }
.prev-table th, .prev-table td { border: 1px solid #dcdfe6; padding: 5px 8px; text-align: center; font-size: 12.5px; vertical-align: middle; }
.prev-table th { background: #f5f7fa; font-weight: 600; }
.prev-table .prev-total { background: #f0f7ff; font-weight: 600; }
.prev-narr { white-space: pre-wrap; color: #606266; }
.docx-preview { font-size: 13px; line-height: 1.8; color: #303133; }
.docx-preview h3 { font-size: 15px; margin: 16px 0 8px; border-left: 3px solid #409eff; padding-left: 8px; }
.docx-preview p { margin: 6px 0; }
.prev-foot { margin-top: 16px; text-align: right; }

/* 录入结果矩阵 */
.result-entry { font-size: 13px; }
.re-def { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 12px; flex-wrap: wrap; }
.re-def-col { flex: 1 1 240px; }
.re-label { font-size: 12px; color: #606266; margin-bottom: 4px; }
.re-def-btns { flex: 0 0 auto; display: flex; flex-direction: column; gap: 6px; }
.re-grid { margin-bottom: 12px; }
.conv-cell { display: flex; flex-direction: column; gap: 2px; }
.conv-arrow { font-size: 11px; color: #909399; text-align: center; line-height: 1.2; }
/* 定性试验（COI）阴阳性显示 */
.qual-cell { display: flex; align-items: center; gap: 6px; }
.pn-badge {
  flex: 0 0 auto; min-width: 22px; height: 22px; line-height: 22px; text-align: center;
  border-radius: 4px; font-size: 12px; font-weight: 700;
}
.pn-pos { background: #fef0f0; color: #f56c6c; border: 1px solid #fbc4c4; }
.pn-neg { background: #f0f9eb; color: #67c23a; border: 1px solid #c2e7b0; }
.pn-none { background: #f4f4f5; color: #909399; border: 1px solid #e9e9eb; }
.re-grid :deep(.el-input__wrapper) { box-shadow: none; }
.re-grid :deep(.el-table__cell) { padding: 2px 0; }
.re-meta { display: flex; flex-wrap: wrap; gap: 14px; align-items: center; margin-top: 6px; }
.re-meta-item { display: flex; align-items: center; gap: 6px; }
.re-meta-item > span { font-size: 12px; color: #606266; white-space: nowrap; }
.re-meta-item .el-input, .re-meta-item .el-date-editor { width: 130px; }
</style>
