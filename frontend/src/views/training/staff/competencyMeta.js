// 人员能力评估（BG-KS-PX-808）公共元信息：主表单与打印组件共用，避免两处漂移

// 生免组岗位（可多选）
export const postOptions = [
  '生化流水线岗', '急诊岗', '病房岗', '糖化电泳岗',
  '凝血流水线岗', '免疫岗', '产前血清学筛查', '质谱岗',
]

// 评分分组（4 类 20 项，每项 0-5 分，合计 100 分；≥80 合格）
export const groups = [
  { title: '职业道德', weight: 25, items: ['遵守法律法规情况和医院、科室规章制度情况', '执行体系文件情况', '检验活动公正性执行情况', '工作态度', '保密工作执行情况'] },
  { title: '专业技术水平', weight: 50, items: ['参加培训和继续教育情况', '观察常规工作现场实际操作情况', '检验特定样品的能力（已检验样品、EQA样品、比对样品）', '核查记录填写情况', '观察设备维护和功能检查情况', '监控检验结果的记录和报告过程', '对检验结果的分析和判断能力', '信息系统使用、新增功能使用、信息安全防护的能力', '执行应急预案的能力', '解决问题的能力'] },
  { title: '员工的表现', weight: 15, items: ['服务对象满意度情况', '团队合作情况', '个人发展情况'] },
  { title: '主要工作业绩', weight: 10, items: ['履行职责工作任务完成情况', '对科室的贡献情况'] },
]
export const allItems = groups.flatMap((g) => g.items)

// 5 种评估方法（源自 CNAS-CL02:2023 6.2 人员能力评估）
export const methodOptions = [
  { value: 'observation', label: '直接观察' },
  { value: 'blind_sample', label: '盲样/未知样测试' },
  { value: 'internal_comparison', label: '内部比对/人员间比对' },
  { value: 'pt_eqa', label: 'PT/EQA 表现' },
  { value: 'data_analysis', label: '数据分析' },
]
// 需要填关联编号的方法
const methodsNeedingRefId = new Set(['blind_sample', 'internal_comparison', 'pt_eqa'])
export function needsRefId(method) { return methodsNeedingRefId.has(method) }
export function methodLabel(v) {
  const m = methodOptions.find((x) => x.value === v)
  return m ? m.label : ''
}

// 各评分项的推荐评估方法 + 依据描述模板：默认直接沿用，个别按实际修改即可
export const defaultEvidenceMap = {
  // 职业道德（25 分 / 5 项）
  '遵守法律法规情况和医院、科室规章制度情况': ['observation', '日常考勤、交接班及科室例会记录完整，本年度无违规违纪记录。'],
  '执行体系文件情况': ['observation', '现场抽查 SOP 与记录表格执行情况，操作与现行体系文件一致，无偏离。'],
  '检验活动公正性执行情况': ['observation', '未发现影响检验公正性的利益冲突或干预，公正性声明执行到位。'],
  '工作态度': ['observation', '日常工作主动负责，服从安排，按时完成分配任务，无推诿拖延。'],
  '保密工作执行情况': ['observation', '患者信息及检验数据按授权范围使用，无泄露或违规外传事件。'],
  // 专业技术水平（50 分 / 10 项）
  '参加培训和继续教育情况': ['data_analysis', '本年度参加专业组培训 __ 次、科室培训 __ 次，继教学分达标。'],
  '观察常规工作现场实际操作情况': ['observation', '20__-__-__ 旁站观察常规操作，流程规范、符合 SOP，无需纠正。'],
  '检验特定样品的能力（已检验样品、EQA样品、比对样品）': ['pt_eqa', '本年度 EQA/PT 回报 __ 项、合格 __ 项，无不合格项。'],
  '核查记录填写情况': ['data_analysis', '抽查记录表格 __ 份，填写完整可追溯，修改规范、签字齐全。'],
  '观察设备维护和功能检查情况': ['observation', '现场观察日常维护与功能检查，按计划执行，记录完整及时。'],
  '监控检验结果的记录和报告过程': ['data_analysis', '抽查检验结果记录与报告 __ 份，录入准确、审核及时，无差错。'],
  '对检验结果的分析和判断能力': ['internal_comparison', '人员比对/留样再测 __ 次，结果一致，偏差在允许范围内。'],
  '信息系统使用、新增功能使用、信息安全防护的能力': ['observation', '熟练使用 LIS 及本年度新增功能，账号与数据安全管理符合要求。'],
  '执行应急预案的能力': ['observation', '参加应急演练 __ 次（断电/仪器故障/生物安全等），处置流程正确。'],
  '解决问题的能力': ['observation', '能独立判断并处理常见异常（复检、干扰、危急值、仪器报警等）。'],
  // 员工的表现（15 分 / 3 项）
  '服务对象满意度情况': ['data_analysis', '临床/患者满意度调查 __ 分，本年度无有效投诉。'],
  '团队合作情况': ['observation', '配合组内排班与带教工作，沟通顺畅，无协作问题。'],
  '个人发展情况': ['data_analysis', '本年度参加继续教育/学术活动 __ 次，取得学分 __ 分。'],
  // 主要工作业绩（10 分 / 2 项）
  '履行职责工作任务完成情况': ['data_analysis', '年度岗位职责与工作任务完成率 100%，无延误或漏项。'],
  '对科室的贡献情况': ['data_analysis', '参与科室质量改进/体系工作 __ 项（内审、SOP 修订、新项目开展等）。'],
}

export function defaultEvidence(it) {
  const d = defaultEvidenceMap[it]
  return { method: d ? d[0] : 'observation', evidence: d ? d[1] : '', ref_id: '', assessor: '', date: '' }
}

// 岗位字符串 ⇄ 数组（库中以顿号分隔存储，兼容逗号/斜杠的老数据）
export function splitPost(s) {
  return String(s || '').split(/[、,，/]/).map((x) => x.trim()).filter(Boolean)
}
export function joinPost(arr) {
  return (arr || []).join('、')
}
