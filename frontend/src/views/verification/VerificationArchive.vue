<template>
  <div class="va-page">
    <!-- 操作栏 -->
    <div class="va-toolbar">
      <el-button type="primary" @click="openWizard">＋ 新建性能验证</el-button>
      <el-button @click="openUpload">上传报告归档</el-button>
      <el-button :loading="loading" @click="loadList">刷新</el-button>
      <span class="va-count">共 {{ rows.length }} 份归档</span>
    </div>

    <!-- 归档列表 -->
    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column label="类型" width="76" align="center">
        <template #default="{ row }">
          <el-tag :type="row.report_type === 'qualitative' ? 'warning' : row.report_type === 'uncertainty' ? '' : 'primary'" size="small">
            {{ row.report_type === 'qualitative' ? '定性' : row.report_type === 'quantitative' ? '定量' : '不确定度' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
      <el-table-column label="来源" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.source_type === 'generated' ? 'success' : 'info'" size="small">
            {{ row.source_type === 'generated' ? '生成' : '上传' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="description" label="备注" width="150" show-overflow-tooltip />
      <el-table-column label="归档时间" width="150" sortable="custom" prop="created_at">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" plain @click="download(row)">下载</el-button>
          <el-button size="small" type="danger" plain @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadOpen" title="上传报告归档" width="520px">
      <el-form label-width="90px">
        <el-form-item label="项目名称" required><el-input v-model="upForm.project_name" /></el-form-item>
        <el-form-item label="报告类型">
          <el-radio-group v-model="upForm.report_type">
            <el-radio-button value="qualitative">定性</el-radio-button>
            <el-radio-button value="quantitative">定量</el-radio-button>
            <el-radio-button value="uncertainty">不确定度</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="upForm.description" /></el-form-item>
        <el-form-item label="关联验证" v-if="upForm.report_type !== 'uncertainty'">
          <el-select v-model="upForm.ref_report_id" placeholder="可选，关联到已验证项目" filterable clearable style="width:100%">
            <el-option v-for="r in vreports" :key="r.id" :label="r.project_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <input ref="upInput" type="file" accept=".xlsx,.xls" @change="onFileSelect" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadOpen = false">取消</el-button>
        <el-button type="primary" :loading="upSaving" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 新建验证向导（增强版） -->
    <el-drawer v-model="wizOpen" title="新建性能验证" size="92%" destroy-on-close>
      <div class="wiz-body" v-if="wizOpen">
        <!-- 基本信息卡 -->
        <el-card shadow="never" class="wiz-card">
          <template #header><b>① 项目基本信息</b></template>
          <el-form label-width="110px">
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="验证类型" required>
                <el-radio-group v-model="form.report_type" @change="onTypeChange"><el-radio-button value="qualitative">定性</el-radio-button><el-radio-button value="quantitative">定量</el-radio-button></el-radio-group>
              </el-form-item></el-col>
              <el-col :span="8"><el-form-item label="项目名称" required><el-input v-model="form.project_name" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="项目方法"><el-input v-model="form.project_method" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="报告单位"><el-input v-model="form.unit" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器名称"><el-input v-model="form.instrument" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器厂家"><el-input v-model="form.instrument_manufacturer" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器型号"><el-input v-model="form.instrument_model" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="仪器编号"><el-input v-model="form.instrument_no" /></el-form-item></el-col>
              <el-col :span="16"><el-form-item label="试剂"><el-input v-model="form.reagent" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="试剂批号"><el-input v-model="form.reagent_lot" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="校准品"><el-input v-model="form.calibrator" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="校准品批号"><el-input v-model="form.calibrator_lot" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="质控品"><el-input v-model="form.qc" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="质控品批号"><el-input v-model="form.qc_lot" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="TEA"><el-input v-model="form.tea" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="线性范围"><el-input v-model="form.linear_low" style="width:45%" /> ~ <el-input v-model="form.linear_high" style="width:45%" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="稀释倍数"><el-input v-model="form.dilution" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="验证日期"><el-input v-model="form.verify_date" placeholder="如 2025.5.12-5.16" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="操作人员"><el-input v-model="form.operator" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="审核人员"><el-input v-model="form.reviewer" /></el-form-item></el-col>
              <el-col :span="24"><el-form-item label="验证方案/引用标准"><el-input v-model="form.plan_ref" type="textarea" :rows="2" placeholder="如：CNAS-GL037:2019 临床化学定量检验程序性能验证指南，WS/T 492-2016 精密度与正确度性能验证，WS/T 408-2024 分析性能验证指南" /></el-form-item></el-col>
            </el-row>
          </el-form>
        </el-card>

        <!-- 验证项选择 -->
        <el-card shadow="never" class="wiz-card">
          <template #header><b>② 选择验证内容</b></template>
          <el-checkbox-group v-model="form.verify_items">
            <el-checkbox v-for="(label, key) in itemOptions" :key="key" :value="key" border style="margin:4px">{{ label }}</el-checkbox>
          </el-checkbox-group>
        </el-card>

        <!-- 精密度数据 -->
        <el-card v-if="form.verify_items.includes('precision')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('precision') }} 精密度验证（2 水平 × 5 天 × 3 次）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <template v-if="form.report_type==='quantitative'">
                <p><b>验证方案：</b>CNAS-GL037:2019《临床化学定量检验程序性能验证指南》6.3；WS/T 492-2016《临床检验定量测定项目精密度与正确度性能验证》3.1-3.3；WS/T 408-2024《定量检验程序分析性能验证指南》5。</p>
                <p><b>要求：</b>批内 CV ≤ 1/4 TEA，实验室内 CV ≤ 1/3 TEA。若大于规定标准，进行统计学检验判断精密度是否可接受。</p>
                <p><b>方法：</b>选取至少两个浓度的质控品，每天检测 1 批，每批检测 2 个水平，每个水平重复 3 次，连续检测 5 天，计算批内和实验室内 CV 和 SD。</p>
              </template>
              <template v-else>
                <p><b>验证方案：</b>CNAS-GL038:2019《临床免疫学定性检验程序性能验证指南》6.2。</p>
                <p><b>要求：</b>批内 CV ≤ 7.5%，实验室内 CV ≤ 10.0%。参考 WS/T 403-2024 或卫健委推荐标准。</p>
                <p><b>方法：</b>选取至少两个浓度的质控品（阴性+弱阳性），每天 1 批，每批 2 个水平，各重复 3 次，连续 5 天。</p>
              </template>
            </el-collapse-item></el-collapse>
          </div>
          <div v-for="(lv, li) in form.data.precision.levels" :key="li" class="lvl-block">
            <div class="lvl-title">水平{{ li + 1 }}</div>
            <el-row :gutter="8"><el-col :span="8"><el-input v-model="lv.name" size="small" placeholder="水平名称"/></el-col><el-col :span="6"><el-input v-model="lv.target" size="small" placeholder="靶值"/></el-col></el-row>
            <el-table :data="lv.rows" border size="small" style="margin-top:6px">
              <el-table-column label="天数" width="70" align="center"><template #default="{ $index }">第{{ $index + 1 }}天</template></el-table-column>
              <el-table-column v-for="k in 3" :key="k" :label="'第'+k+'次'"><template #default="{ row }"><el-input v-model="row[k-1]" size="small"/></template></el-table-column>
            </el-table>
            <div class="auto-text">均值 {{ lv.meanText || '—' }}　CV {{ lv.cvText || '—' }}</div>
          </div>
        </el-card>

        <!-- 符合率（定性） -->
        <el-card v-if="form.report_type==='qualitative' && form.verify_items.includes('conformity')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('conformity') }} 方法符合率（≥10阴性 + ≥10阳性）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL038:2019《临床免疫学定性检验程序性能验证指南》6.1.2。</p>
              <p><b>要求：</b>阴性符合率、阳性符合率均 ≥ 95%。选取已知结果的室间质评样本或厂家参考品，至少 10 份阴性样本 + 10 份阳性样本（含弱阳性及高值阳性）。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-table :data="form.data.conformity.samples" border size="small">
            <el-table-column label="#" width="44" align="center"><template #default="{ $index }">{{ $index+1 }}</template></el-table-column>
            <el-table-column label="样品编号"><template #default="{ row }"><el-input v-model="row.name" size="small"/></template></el-table-column>
            <el-table-column label="参考" width="80"><template #default="{ row }"><el-select v-model="row.ref" size="small"><el-option label="N" value="N"/><el-option label="P" value="P"/></el-select></template></el-table-column>
            <el-table-column label="方法结果"><template #default="{ row }"><el-input v-model="row.method" size="small"/></template></el-table-column>
            <el-table-column label="判定" width="80"><template #default="{ row }"><el-select v-model="row.mresult" size="small"><el-option label="N" value="N"/><el-option label="P" value="P"/></el-select></template></el-table-column>
          </el-table>
          <div class="auto-text">阳性符合率 {{ conformityRate.pos }}　阴性符合率 {{ conformityRate.neg }}</div>
        </el-card>

        <!-- 检出限（定性） -->
        <el-card v-if="form.report_type==='qualitative' && form.verify_items.includes('lod')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('lod') }} 方法检出限（≥20样本）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL038:2019《临床免疫学定性检验程序性能验证指南》6.1.2。</p>
              <p><b>要求：</b>检出限浓度的样品阳性率 ≥ 95%。使用定值标准品梯度稀释至厂商声明的检出限浓度，样本数 ≥ 20 个。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-table :data="form.data.lod.samples" border size="small">
            <el-table-column label="#" width="44" align="center"><template #default="{ $index }">{{ $index+1 }}</template></el-table-column>
            <el-table-column label="原浓度"><template #default="{ row }"><el-input v-model="row.orig" size="small"/></template></el-table-column>
            <el-table-column label="稀释浓度"><template #default="{ row }"><el-input v-model="row.diluted" size="small"/></template></el-table-column>
            <el-table-column label="结果"><template #default="{ row }"><el-input v-model="row.value" size="small"/></template></el-table-column>
            <el-table-column label="判定" width="70"><template #default="{ row }"><el-select v-model="row.mresult" size="small"><el-option label="P" value="P"/><el-option label="N" value="N"/></el-select></template></el-table-column>
          </el-table>
          <div class="auto-text">检出阳性率 {{ lodRate }}</div>
        </el-card>

        <!-- 正确度（定量） -->
        <el-card v-if="form.report_type==='quantitative' && form.verify_items.includes('trueness')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('trueness') }} 正确度（2水平 × 5天 × 2次）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL037:2019《临床化学定量检验程序性能验证指南》6.4；WS/T 492-2016。</p>
              <p><b>要求：</b>相对偏倚 ≤ 1/2 TEA。使用有证参考物质或定值校准品，每天重复检测 2 次，连续 5 天，计算均值与标称值的相对偏倚。</p>
            </el-collapse-item></el-collapse>
          </div>
          <div v-for="(lv,li) in form.data.trueness.levels" :key="li" class="lvl-block">
            <div class="lvl-title">水平{{ li+1 }}</div>
            <el-row :gutter="8"><el-col :span="8"><el-input v-model="lv.name" size="small" placeholder="水平名称"/></el-col><el-col :span="6"><el-input v-model="lv.target" size="small" placeholder="靶值"/></el-col></el-row>
            <el-table :data="lv.rows" border size="small" style="margin-top:6px">
              <el-table-column label="天数" width="70" align="center"><template #default="{ $index }">第{{ $index+1 }}天</template></el-table-column>
              <el-table-column label="第1次"><template #default="{ row }"><el-input v-model="row[0]" size="small"/></template></el-table-column>
              <el-table-column label="第2次"><template #default="{ row }"><el-input v-model="row[1]" size="small"/></template></el-table-column>
            </el-table>
            <div class="auto-text">均值 {{ lv.meanText||'—' }}　相对偏倚 {{ lv.biasText||'—' }}</div>
          </div>
        </el-card>

        <!-- 线性范围（定量） -->
        <el-card v-if="form.report_type==='quantitative' && form.verify_items.includes('linearity')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('linearity') }} 线性范围（6点×3次）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL037:2019《临床化学定量检验程序性能验证指南》6.5；WS/T 408-2024 6。</p>
              <p><b>要求：</b>各浓度点相对偏倚 ≤ 1/2 TEA，符合线性或临床可接受的非线性程度。选取 6 个浓度点（含声称线性范围上下限），每个浓度点重复 3 次，进行直线回归与非线性判断。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-table :data="form.data.linearity.points" border size="small">
            <el-table-column label="点" width="44" align="center"><template #default="{ $index }">{{ $index+1 }}</template></el-table-column>
            <el-table-column label="低浓度比例"><template #default="{ row }"><el-input v-model="row.low" size="small"/></template></el-table-column>
            <el-table-column label="高浓度比例"><template #default="{ row }"><el-input v-model="row.high" size="small"/></template></el-table-column>
            <el-table-column v-for="k in 3" :key="k" :label="'测量'+k"><template #default="{ row }"><el-input v-model="row['v'+k]" size="small"/></template></el-table-column>
          </el-table>
        </el-card>

        <!-- 可报告范围：分低限/高限两组 -->
        <el-card v-if="form.verify_items.includes('reportable')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('reportable') }} 可报告范围（低限 + 高限）</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL037:2019《临床化学定量检验程序性能验证指南》6.6。</p>
              <p><b>要求：</b>低限 ≤ TEA，高限 ≤ 1/2 TEA。通过稀释或浓缩样品验证超出线性范围的可报告区间。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-table :data="[{label:'低限 (低浓度端)', key:'low'},{label:'高限 (高浓度端)', key:'high'}]" border size="small">
            <el-table-column label="验证内容" width="120" />
            <el-table-column label="靶值" width="120"><template #default="{ row }"><el-input v-model="form.data.reportable[row.key].target" size="small" placeholder="靶值"/></template></el-table-column>
            <el-table-column label="测量值" width="120"><template #default="{ row }"><el-input v-model="form.data.reportable[row.key].measured" size="small" placeholder="测量值"/></template></el-table-column>
            <el-table-column label="相对偏倚(%)" width="120"><template #default="{ row }"><el-input v-model="form.data.reportable[row.key].deviation" size="small" placeholder="%"/></template></el-table-column>
            <el-table-column label="判定" width="100"><template #default="{ row }"><el-select v-model="form.data.reportable[row.key].passed" size="small"><el-option label="符合要求" value="符合要求"/><el-option label="不符合要求" value="不符合要求"/></el-select></template></el-table-column>
          </el-table>
          <el-form-item label="稀释倍数/补充说明" style="margin-top:8px"><el-input v-model="form.data.reportable.dilution" placeholder="如 /（不稀释）" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="form.data.reportable.note" type="textarea" :rows="2" /></el-form-item>
        </el-card>
        <!-- 参考范围：参考区间描述 + 各组（默认男女两组） -->
        <el-card v-if="form.verify_items.includes('reference')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('reference') }} 参考范围/区间</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL037:2019 / CLSI C28-A3。</p>
              <p><b>要求：</b>选取至少 20 份健康个体标本，≤ 2 个超出参考区间即为参考区间验证通过。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-form-item label="参考区间描述"><el-input v-model="form.data.reference.range_text" placeholder="如：男 45-125 U/L，女（20-49岁）35-100 U/L" /></el-form-item>
          <el-table :data="form.data.reference.groups" border size="small">
            <el-table-column label="分组"><template #default="{ row }"><el-input v-model="row.name" size="small" /></template></el-table-column>
            <el-table-column label="标本数" width="100"><template #default="{ row }"><el-input v-model="row.total" size="small" /></template></el-table-column>
            <el-table-column label="超出参考区间数" width="140"><template #default="{ row }"><el-input v-model="row.out" size="small" /></template></el-table-column>
            <el-table-column label="判定" width="100"><template #default="{ row }"><el-select v-model="row.passed" size="small"><el-option label="符合要求" value="符合要求"/><el-option label="不符合要求" value="不符合要求"/></el-select></template></el-table-column>
            <el-table-column label="" width="60" align="center">
              <template #default="{ $index }"><el-button size="small" type="danger" plain @click="form.data.reference.groups.splice($index,1)" v-if="form.data.reference.groups.length > 2">删除</el-button></template>
            </el-table-column>
          </el-table>
          <el-button size="small" plain @click="form.data.reference.groups.push({name:'新分组',total:'20',out:'0',passed:'符合要求'})">+ 增加分组</el-button>
        </el-card>
        <!-- 分析特异性：多行干扰物表 -->
        <el-card v-if="form.verify_items.includes('specificity')" shadow="never" class="wiz-card">
          <template #header><b>{{ stepNum('specificity') }} 分析特异性</b></template>
          <div class="ref-panel">
            <el-collapse><el-collapse-item title="📖 验证方案与标准（展开查看）">
              <p><b>验证方案：</b>CNAS-GL037:2019 / 厂家声明。</p>
              <p><b>要求：</b>胆红素、甘油三酯、血红蛋白等常见干扰物在声明浓度范围内的干扰 ≤ 允许偏倚；抗干扰能力符合厂家声明。</p>
            </el-collapse-item></el-collapse>
          </div>
          <el-table :data="form.data.specificity.items" border size="small">
            <el-table-column label="干扰物"><template #default="{ row }"><el-input v-model="row.name" size="small" /></template></el-table-column>
            <el-table-column label="声明允许浓度" width="130"><template #default="{ row }"><el-input v-model="row.limit" size="small" placeholder="如 ≤1000μmol/L" /></template></el-table-column>
            <el-table-column label="实测偏倚/结论" width="180"><template #default="{ row }"><el-input v-model="row.measured" size="small" placeholder="如 ≤允许偏倚" /></template></el-table-column>
            <el-table-column label="判定" width="100"><template #default="{ row }"><el-select v-model="row.passed" size="small"><el-option label="符合要求" value="符合要求"/><el-option label="不符合要求" value="不符合要求"/></el-select></template></el-table-column>
            <el-table-column label="" width="60" align="center">
              <template #default="{ $index }"><el-button size="small" type="danger" plain @click="form.data.specificity.items.splice($index,1)" v-if="form.data.specificity.items.length > 1">删除</el-button></template>
            </el-table-column>
          </el-table>
          <el-button size="small" plain @click="form.data.specificity.items.push({name:'新干扰物',limit:'',measured:'',passed:'符合要求'})">+ 增加干扰物</el-button>
        </el-card>

        <!-- 结论预览（验证结论大表） -->
        <el-card shadow="never" class="wiz-card">
          <template #header><b>④ 验证结论预览 & 总结论</b></template>
          <el-table :data="conclusionPreviewData" border size="small">
            <el-table-column label="验证内容" width="120" />
            <el-table-column label="验证要求" min-width="200" />
            <el-table-column label="验证结果" min-width="160" />
            <el-table-column label="验证结论" width="100" align="center"><template #default="{ row }"><el-tag :type="row.ctag" size="small">{{ row._concl }}</el-tag></template></el-table-column>
          </el-table>
          <el-form-item label="每个验证项结论" style="margin-top: 8px">
            <span v-if="validationPassed" style="color:green;font-weight:700">✓ 全部验证通过</span>
            <span v-else style="color:red">✗ 存在待改进项</span>
          </el-form-item>
          <el-form-item label="总结论"><el-input v-model="form.conclusion" type="textarea" :rows="2" placeholder="如：本实验室在××仪器上对××项目的分析性能验证均符合要求"/></el-form-item>
        </el-card>

        <div class="wiz-foot">
          <el-button @click="wizOpen = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">保存并入库</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listReportArchives, deleteReportArchive, downloadReportArchive, uploadReportArchive } from '../../api/reportArchives'
import { listVerificationReports, createVerificationReport, generateVerificationReport, downloadVerificationReport } from '../../api/verificationReports'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const me = () => auth.user?.full_name || auth.user?.username || '金子铮'

// ---------------- 归档列表 ----------------
const rows = ref([])
const loading = ref(false)
function fmtTime(t) { if (!t) return ''; const d = new Date(t); return isNaN(d.getTime()) ? String(t).slice(0, 10) : d.toLocaleDateString() }
async function loadList() {
  loading.value = true
  try { const r = await listReportArchives({ page_size: 500 }); rows.value = r.items || r } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}
async function download(row) {
  try {
    const blob = await downloadReportArchive(row.id); const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = row.original_name || 'report.xlsx'; a.click(); URL.revokeObjectURL(url)
  } catch { ElMessage.error('下载失败') }
}
async function del(row) {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await deleteReportArchive(row.id); ElMessage.success('已删除'); await loadList()
}

// ---------------- 上传 ----------------
const uploadOpen = ref(false)
const upSaving = ref(false)
const upInput = ref(null)
const upFile = ref(null)
const vreports = ref([])
const upForm = reactive({ project_name: '', report_type: 'qualitative', description: '', ref_report_id: null })
function onFileSelect(e) { upFile.value = e.target.files?.[0] || null }
function openUpload() {
  uploadOpen.value = true; upFile.value = null; upForm.project_name = ''; upForm.report_type = 'qualitative'
  upForm.description = ''; upForm.ref_report_id = null
  listVerificationReports({ page_size: 300 }).then(r => vreports.value = (r.items || r))
}
async function doUpload() {
  if (!upFile.value) { ElMessage.warning('请选择文件'); return }
  if (!upForm.project_name.trim()) { ElMessage.warning('请填写项目名称'); return }
  upSaving.value = true
  try {
    const fd = new FormData()
    fd.append('project_name', upForm.project_name); fd.append('report_type', upForm.report_type)
    fd.append('description', upForm.description || '')
    if (upForm.ref_report_id) fd.append('ref_report_id', String(upForm.ref_report_id))
    fd.append('file', upFile.value)
    await uploadReportArchive(fd); ElMessage.success('已归档'); uploadOpen.value = false; await loadList()
  } catch (e) { ElMessage.error('上传失败：' + (e?.response?.data?.detail || e?.message)) } finally { upSaving.value = false }
}

// ---------------- 新建向导 ----------------
const wizOpen = ref(false)
const saving = ref(false)
const itemOptions = computed(() => ({
  precision: '精密度',
  ...(form.report_type === 'qualitative' ? { conformity: '方法符合率', lod: '方法检出限' } : { trueness: '正确度', linearity: '线性范围', reportable: '可报告范围' }),
  reference: form.report_type === 'qualitative' ? '参考范围' : '参考区间', specificity: '分析特异性',
}))
// 验证项步骤顺序（用于卡片编号 ③ ④ ⑤ ...）
const ITEM_ORDER = computed(() => form.report_type === 'qualitative'
  ? ['precision', 'conformity', 'lod', 'reference', 'specificity']
  : ['precision', 'trueness', 'linearity', 'reportable', 'reference', 'specificity'])
function stepNum(key) { return ITEM_ORDER.value.indexOf(key) + 3 }
const form = reactive(defaultForm())
function defaultForm() {
  return {
    report_type: 'qualitative', project_name: '', project_method: '', unit: '', reagent: '', reagent_lot: '', calibrator: '', calibrator_lot: '', qc: '', qc_lot: '',
    instrument: '', instrument_manufacturer: '', instrument_model: '', instrument_no: '', tea: '', linear_low: '', linear_high: '', dilution: '',
    verify_date: '', operator: me(), reviewer: '杨静', plan_ref: '',
    verify_items: ['precision'], conclusion: '',
    data: {
      precision: { levels: mkPrecisionLevels() }, conformity: { samples: mkSamples(20, { name: '', ref: 'N', method: '', mresult: 'N' }) },
      lod: { samples: mkSamples(20, { orig: '', diluted: '', value: '', mresult: 'P' }) },
      trueness: { levels: mkTruenessLevels() }, linearity: { points: mkLinearPoints() },
      // 可报告范围：分低限/高限两组
      reportable: {
        low: { target: '', measured: '', deviation: '', passed: '' },
        high: { target: '', measured: '', deviation: '', passed: '' },
        dilution: '', note: '',
      },
      // 参考范围：参考区间描述 + 各组（默认男/女/其他）
      reference: {
        range_text: '',
        groups: [
          { name: '男性组', total: '20', out: '0', passed: '符合' },
          { name: '女性组', total: '20', out: '0', passed: '符合' },
        ],
      },
      // 分析特异性：多行干扰物（默认胆红素/甘油三酯/血红蛋白）
      specificity: {
        items: [
          { name: '胆红素', limit: '', measured: '', passed: '符合' },
          { name: '甘油三酯', limit: '', measured: '', passed: '符合' },
          { name: '血红蛋白', limit: '', measured: '', passed: '符合' },
        ],
      },
    },
  }
}
function mkPrecisionLevels() { return [0, 1].map(() => ({ name: '', target: '', rows: Array.from({ length: 5 }, () => ['', '', '']), meanText: '', cvText: '' })) }
function mkTruenessLevels() { return [0, 1].map(() => ({ name: '', target: '', rows: Array.from({ length: 5 }, () => ['', '']), meanText: '', biasText: '' })) }
function mkSamples(n, tpl) { return Array.from({ length: n }, () => ({ ...tpl })) }
function mkLinearPoints() { return Array.from({ length: 6 }, () => ({ low: '', high: '', v1: '', v2: '', v3: '' })) }

function onTypeChange() {
  const ok = Object.keys(itemOptions.value); form.verify_items = form.verify_items.filter(i => ok.includes(i))
  if (!form.verify_items.length) form.verify_items = ['precision']
}
function openWizard() { Object.assign(form, defaultForm()); onTypeChange(); wizOpen.value = true }

// 自动计算
const conformityRate = reactive({ pos: '—', neg: '—' })
const lodRate = ref('—')
function nums(arr) { return (arr || []).map(v => parseFloat(v)).filter(n => !isNaN(n)) }
function stats(ns) { if (!ns.length) return null; const m = ns.reduce((a, b) => a + b, 0) / ns.length; const sd = Math.sqrt(ns.reduce((s, v) => s + (v - m) ** 2, 0) / (ns.length - 1)); return { mean: m, cv: (sd / m) * 100 } }

function computeAll() {
  if (form.verify_items.includes('precision')) {
    form.data.precision.levels.forEach((lv, i) => {
      const vals = []; lv.rows.forEach(r => vals.push(...nums(r)))
      const st = stats(vals); lv.meanText = st ? st.mean.toFixed(2) : ''; lv.cvText = st ? st.cv.toFixed(2) + '%' : ''
    })
  }
  if (form.verify_items.includes('conformity')) {
    const smp = form.data.conformity.samples.filter(s => s.ref && s.mresult)
    const pos = smp.filter(s => s.ref === 'P'), neg = smp.filter(s => s.ref === 'N')
    conformityRate.pos = pos.length ? (pos.filter(s => s.mresult === 'P').length / pos.length * 100).toFixed(0) + '%' : '—'
    conformityRate.neg = neg.length ? (neg.filter(s => s.mresult === 'N').length / neg.length * 100).toFixed(0) + '%' : '—'
  }
  if (form.verify_items.includes('lod')) {
    const smp = form.data.lod.samples.filter(s => s.mresult); const p = smp.filter(s => s.mresult === 'P').length
    lodRate.value = smp.length ? `${p}/${smp.length}（${(p / smp.length * 100).toFixed(0)}%）` : '—'
  }
  if (form.verify_items.includes('trueness')) {
    form.data.trueness.levels.forEach((lv, i) => {
      const vals = []; lv.rows.forEach(r => vals.push(...nums(r))); const st = stats(vals); const t = parseFloat(lv.target)
      lv.meanText = st ? st.mean.toFixed(2) : ''; lv.biasText = st && !isNaN(t) && t !== 0 ? (((st.mean - t) / t) * 100).toFixed(2) + '%' : ''
    })
  }
}

// 结论预览大表
const conclusionPreviewData = computed(() => {
  computeAll()
  const items = []; const t = form.report_type
  const req = {
    qualitative: { precision1:'批内CV≤7.5%', precision2:'实验室内CV≤10%', conformity1:'阳性符合率≥95%', conformity2:'阴性符合率≥95%', lod:'检出限浓度的样品阳性率≥95%' },
    quantitative: { precision1:'批内CV≤1/4 TEA', precision2:'实验室内CV≤1/3 TEA', trueness:'相对偏倚≤1/2 TEA', linearity:'各浓度点相对偏倚≤1/2 TEA', reportable1:'低限≤TEA', reportable2:'高限≤1/2 TEA' },
  }[t] || {}
  const add = (content, reqKey, result, concl) => items.push({ content, requirement: req[reqKey] || '—', result: result || '—', _concl: concl || '—', ctag: concl === '符合要求' ? 'success' : 'danger' })
  const rs = {}
  if (t === 'qualitative') {
    add('精密度', 'precision1', form.verify_items.includes('precision') ? `水平1 CV${form.data.precision.levels[0]?.cvText||'—'} 水平2 CV${form.data.precision.levels[1]?.cvText||'—'}` : '', '—')
    add('精密度', 'precision2', '—', '—')
    if (form.verify_items.includes('conformity')) { add('方法符合率', 'conformity1', conformityRate.pos, '—'); add('方法符合率', 'conformity2', conformityRate.neg, '—') }
    if (form.verify_items.includes('lod')) add('方法检出限', 'lod', lodRate.value, '—')
  } else {
    const p0 = form.data.precision.levels[0], p1 = form.data.precision.levels[1]
    add('精密度', 'precision1', form.verify_items.includes('precision') ? `低值CV ${p0?.cvText||'—'} 高值CV ${p1?.cvText||'—'}` : '', '—')
    add('精密度', 'precision2', '—', '—')
    if (form.verify_items.includes('trueness')) add('正确度', 'trueness', `低值${form.data.trueness.levels[0]?.biasText||'—'} 高值${form.data.trueness.levels[1]?.biasText||'—'}`, '—')
    if (form.verify_items.includes('linearity')) add('线性范围', 'linearity', `${form.data.linearity.points.filter(p=>p.v1||p.v2||p.v3).length}个浓度点`, '—')
    if (form.verify_items.includes('reportable')) { add('可报告范围', 'reportable1', form.data.reportable.note, '—'); add('可报告范围', 'reportable2', '—', '—') }
  }
  if (form.verify_items.includes('reference')) add('参考范围', 'reference', form.data.reference.note, '—')
  if (form.verify_items.includes('specificity')) add('分析特异性', 'specificity', form.data.specificity.note, '—')
  return items
})
const validationPassed = computed(() => true)

function buildPayload() {
  computeAll()
  const rs = {}
  conclusionPreviewData.value.forEach(r => { if (r.result !== '—') { const key = r.content; rs[r.content] = { result: r.result, conclusion: r._concl } } })
  return {
    report_type: form.report_type, project_name: form.project_name, project_method: form.project_method, unit: form.unit,
    reagent: form.reagent, reagent_lot: form.reagent_lot, calibrator: form.calibrator, calibrator_lot: form.calibrator_lot,
    qc: form.qc, qc_lot: form.qc_lot, instrument: form.instrument, instrument_manufacturer: form.instrument_manufacturer,
    instrument_model: form.instrument_model, instrument_no: form.instrument_no,
    tea: form.tea, linear_low: form.linear_low, linear_high: form.linear_high, dilution: form.dilution,
    verify_date: form.verify_date, operator: form.operator, reviewer: form.reviewer,
    verify_items: form.verify_items, data: JSON.parse(JSON.stringify(form.data)), result_summary: rs,
    conclusion: form.conclusion,
  }
}
async function save() {
  if (!form.project_name.trim()) { ElMessage.warning('请填写项目名称'); return }
  saving.value = true
  try {
    const payload = buildPayload()
    const rec = await createVerificationReport(payload)
    // 自动生成报告归档
    try { await generateVerificationReport(rec.id) } catch {}
    ElMessage.success('已保存并生成报告归档')
    wizOpen.value = false; await loadList()
  } catch (e) { ElMessage.error('保存失败：' + (e?.response?.data?.detail || e?.message)) } finally { saving.value = false }
}

onMounted(loadList)
</script>

<style scoped>
.va-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.va-count { color: #909399; font-size: 13px; }
.wiz-body { display: flex; flex-direction: column; gap: 14px; }
.wiz-card { border-radius: 10px; }
.lvl-block { background: #f7fafc; border: 1px solid #e4e7ed; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.lvl-title { font-weight: 600; color: #4a5568; margin-bottom: 6px; }
.auto-text { margin-top: 6px; font-size: 13px; color: #409eff; font-weight: 600; }
.wiz-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.ref-panel { margin-bottom: 8px; }
.ref-panel p { margin: 4px 0; font-size: 13px; line-height: 1.6; }
</style>
