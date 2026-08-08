// 维修记录「排查后质控验证」结构化数据的默认结构与摘要生成
// 供 RepairRecordForm.vue（内部弹窗 + 扫码页共用）与两处提交逻辑复用

export function mkQcRow() {
  return { target: '', result: '', control: '' }
}
export function mkCmpRow() {
  return { sample: '', result: '', accept: '' }
}
export function defaultQcDetail() {
  return {
    method: 'qc',
    qc: { project: '', rows: [mkQcRow()] },
    compare: { project: '', rows: Array.from({ length: 5 }, mkCmpRow) },
    calibrate: { project: '', target: '', uncertainty: '', results: ['', '', ''] },
    affect_before: false,
    affect_compare: { project: '', rows: Array.from({ length: 5 }, mkCmpRow) },
  }
}

// 质控验证 → 摘要文本（存入 qc_verification 字段，便于列表/打印展示）
export function buildQcSummary(qd) {
  if (!qd || typeof qd !== 'object') return ''
  const parts = []
  const fmtRows = (rows, isTargetMode) =>
    (rows || [])
      .filter((r) => (isTargetMode ? r.target !== '' || r.result !== '' : r.sample !== '' || r.result !== ''))
      .map((r) => (isTargetMode
        ? `靶值${r.target || '-'}/结果${r.result || '-'}/${r.control || '未判'}`
        : `样本${r.sample || '-'}/结果${r.result || '-'}/${r.accept || '未判'}`))
      .join('；')
  if (qd.method === 'qc') {
    parts.push(`室内质控验证（${qd.qc?.project || '—'}）：${fmtRows(qd.qc?.rows, true) || '未填'}`)
  } else if (qd.method === 'compare') {
    parts.push(`样本比对（${qd.compare?.project || '—'}）：${fmtRows(qd.compare?.rows, false) || '未填'}`)
  } else if (qd.method === 'calibrate') {
    const c = qd.calibrate || {}
    parts.push(`校准验证（${c.project || '—'}）：靶值${c.target || '-'}±${c.uncertainty || '-'}，3次结果${(c.results || []).filter((v) => v !== '').join('/') || '未填'}`)
  }
  if (qd.affect_before) {
    parts.push(`影响维修前结果：是（样本比对 ${qd.affect_compare?.project || '—'}：${fmtRows(qd.affect_compare?.rows, false) || '未填'}）`)
  } else {
    parts.push('影响维修前结果：否')
  }
  return parts.join('；')
}
