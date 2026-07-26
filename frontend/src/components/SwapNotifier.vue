<template>
  <!-- 全局换班消息轮询：仅渲染逻辑，无可见 UI -->
  <span style="display: none" />
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { listSwaps, confirmSwap, rejectSwap } from '../api/scheduling'

const POLL_MS = 30000
let timer = null
const presented = new Set()  // 本次会话已弹出过的换班 id，避免重复打扰

async function check() {
  try {
    const list = await listSwaps({ role: 'pending_in' })
    const pending = (list || []).filter((s) => s.status === '待确认')
    const pendingIds = new Set(pending.map((s) => s.id))
    // 已不再是「待确认」的记录从去重集合中清除（确认/拒绝/取消后不再打扰）
    for (const id of [...presented]) {
      if (!pendingIds.has(id)) presented.delete(id)
    }
    for (const s of pending) {
      if (presented.has(s.id)) continue
      presented.add(s.id)
      await present(s)
    }
  } catch (_) {
    // 鉴权失败/网络异常时静默跳过，下一轮继续
  }
}

function present(s) {
  return ElMessageBox.confirm(
    `${s.from_person} 请求与您换班。\n备注：${s.note || '无'}`,
    '换班申请',
    {
      confirmButtonText: '确认换班',
      cancelButtonText: '拒绝',
      type: 'warning',
      distinguishCancelAndClose: true,
    },
  )
    .then(async () => {
      await confirmSwap(s.id)
      ElMessage.success('已确认换班，班表已更新')
    })
    .catch(async (action) => {
      if (action === 'cancel') {
        await rejectSwap(s.id)
        ElMessage.info('已拒绝该换班')
      }
      // action === 'close'（点击 X）：保持待确认，稍后可在「我的换班」处理
    })
}

onMounted(() => {
  check()
  timer = setInterval(check, POLL_MS)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>
