# -*- coding: utf-8 -*-
"""汇总维修记录按 BG-KS-CZ-909 格式打印"""
import io

p = 'frontend/src/views/instruments/InstrumentList.vue'
s = io.open(p, encoding='utf-8').read()

# 1) 对话框底部加打印按钮
old_footer = """      <template #footer>
        <el-button @click="summaryOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 维修记录详情（汇总入口查看） -->"""
new_footer = """      <template #footer>
        <el-button @click="summaryOpen = false">关闭</el-button>
        <el-button type="primary" @click="printRepairSummary909">打印（BG-KS-CZ-909 格式）</el-button>
      </template>
    </el-dialog>

    <!-- 维修记录详情（汇总入口查看） -->"""
assert old_footer in s, 'dialog footer not found'
s = s.replace(old_footer, new_footer, 1)

# 2) 打印函数
anchor = "function viewRepairDetail(row) {"
fn = '''// ---------------- 按 BG-KS-CZ-909《仪器维修记录表》格式打印 ----------------
const NINE09_NOTE = '1、故障描述：请详细描述故障内容及影响到的项目。2、故障原因及维修过程：详细说明故障处理办法、处理结果、处理完成的日期和时间。如有维修工单也可在工单上标明。3、排查后性能验证过程及结果：3.1 样本的选择：设备修复后，当故障对检验结果的准确性有影响时，根据影响的程度可选择可校准的项目实施校准验证、室内质控验证、至少5份标本与其他仪器的检测比对、以前检验过的样本留样再测等方式中的合适方式。前提是样本结果是正确的。3.2 需要填写故障前后结果数据分析：a) 实施评估的判断：分析仪器故障的类型对检验结果的准确性是否有影响，当没有影响时无须对故障前检验结果进行评估；当故障可能影响检测结果时需对故障前检验结果进行评估。b) 在评估时，至少抽取仪器故障发生前的最后5份标本，相关检测项目重测一次，以该次检验结果为靶值、计算故障前检测结果与该次检测结果的相对百分偏倚，当检测项目有大于或等于80%标本的结果在允许相对百分偏倚范围内时，说明故障前检测结果未受影响。c) 当故障仪器有检测相同项目的另一相同型号仪器时，可用其进行故障前标本的检测。d) 当故障仪器唯一时，根据故障排除时间的长短，对故障前的标本做适当保存，待性能确认正常后进行检测。3.3 经评估确认故障前检测结果未受影响的，检验报告无须处理；若故障会影响之前检测结果，需收回或标识已发出的不符合检验结果，重新发布正确报告，并填写《不符合检测报告评审记录表》。'

function esc909(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\\n/g, '<br/>')
}

function printRepairSummary909() {
  const rows = (summaryRows.value || []).map((r, i) => `
    <tr>
      <td class="num">${i + 1}</td>
      <td>${esc909(r.instrument_name) }</td>
      <td class="num">${esc909(String(r.instrument_dept_no || '').replace('MHZYY-JYK-', ''))}</td>
      <td>${esc909([r.fault_desc, r.affected_items ? '（影响项目：' + r.affected_items + '）' : ''].filter(Boolean).join(' '))}</td>
      <td>${esc909([r.finder, r.found_at].filter(Boolean).join(' '))}</td>
      <td>${esc909(r.notify_repair_at)}</td>
      <td>${esc909(r.handled_at)}</td>
      <td>${esc909(r.cause_process)}</td>
      <td class="num">${esc909(r.repairer)}</td>
      <td>${esc909(r.qc_verification)}</td>
      <td>${esc909(r.restored_at)}</td>
      <td class="num">${esc909(r.signer)}</td>
    </tr>`).join('')

  const html = `
  <style>@page { size: A4 landscape; margin: 8mm; }</style>
  <h2 style="text-align:center;margin:0 0 6px;font-size:16px;">仪器维修记录表</h2>
  <div style="font-size:11px;margin-bottom:4px;">实验室/专业组：检验科生化免疫组　　　　　共 ${(summaryRows.value || []).length} 条</div>
  <table style="border-collapse:collapse;width:100%;font-size:9px;">
    <tr>
      <th style="border:1px solid #333;padding:3px;width:3%;">序号</th>
      <th style="border:1px solid #333;padding:3px;width:9%;">设备名称</th>
      <th style="border:1px solid #333;padding:3px;width:7%;">仪器编号</th>
      <th style="border:1px solid #333;padding:3px;width:11%;">故障描述</th>
      <th style="border:1px solid #333;padding:3px;width:9%;">发现人及<br/>发现时间</th>
      <th style="border:1px solid #333;padding:3px;width:8%;">通知维修时间</th>
      <th style="border:1px solid #333;padding:3px;width:8%;">处理日期及时间</th>
      <th style="border:1px solid #333;padding:3px;width:12%;">故障原因及维修过程</th>
      <th style="border:1px solid #333;padding:3px;width:5%;">维修人</th>
      <th style="border:1px solid #333;padding:3px;width:16%;">排查后性能验证过程及结果</th>
      <th style="border:1px solid #333;padding:3px;width:8%;">恢复使用<br/>日期及时间</th>
      <th style="border:1px solid #333;padding:3px;width:6%;">恢复使用<br/>授权人签名</th>
    </tr>
    ${rows || '<tr><td colspan="12" style="border:1px solid #333;padding:6px;text-align:center;">（无维修记录）</td></tr>'}
  </table>
  <div style="font-size:9px;line-height:1.5;margin-top:8px;">
    <b>表格填写说明：</b>${esc909(NINE09_NOTE)}
  </div>
  <div style="margin-top:10px;border-top:1px solid #999;padding-top:4px;font-size:9px;display:flex;justify-content:space-between;">
    <span>表格编号：BG-KS-CZ-909</span><span>民航总医院检验科</span><span>生效日期：2025.04.01</span>
  </div>`
  printHtml('仪器维修记录表(BG-KS-CZ-909)', html)
}

'''
assert anchor in s
s = s.replace(anchor, fn + anchor, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('909 打印函数已加入')
