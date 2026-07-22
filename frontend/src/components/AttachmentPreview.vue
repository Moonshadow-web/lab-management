<template>
  <el-dialog
    :model-value="visible"
    :title="file?.original_name || '预览'"
    width="90%" top="2vh" append-to-body
    @update:model-value="(v) => emit('update:visible', v)"
  >
    <div v-if="loading" v-loading="true" style="height: 75vh" />
    <template v-else>
      <div v-if="mode === 'image'" style="text-align: center">
        <img :src="src" :alt="file?.original_name" style="max-width: 100%" />
      </div>
      <iframe v-else-if="mode === 'pdf'" :src="src" style="width: 100%; height: 75vh; border: 0" />
      <div v-else-if="mode === 'html'" class="preview-html" v-html="html" />
      <div v-else class="other-preview">
        <el-icon :size="64"><Document /></el-icon>
        <p>{{ fallbackMsg }}</p>
        <el-button type="primary" @click="emit('download', file)">下载 {{ file?.original_name }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import mammoth from 'mammoth'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // 附件对象：{ id, file_type, original_name, ... }
  file: { type: Object, default: null },
  // (id, inline) => url 字符串，由父组件按模块传入（comparison / interlab）
  getUrl: { type: Function, required: true },
})
const emit = defineEmits(['update:visible', 'download'])

const loading = ref(false)
const mode = ref('other') // image | pdf | html | other
const src = ref('')
const html = ref('')
const fallbackMsg = ref('')

function extOf(name) {
  const m = (name || '').toLowerCase().match(/\.([a-z0-9]+)$/)
  return m ? m[1] : ''
}
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
async function fetchBlob(id) {
  const res = await fetch(props.getUrl(id, true), { credentials: 'include' })
  if (!res.ok) throw new Error('文件不存在或预览失败')
  return res.blob()
}

watch(
  () => [props.visible, props.file],
  async ([vis, f]) => {
    if (!vis || !f) return
    await load(f)
  },
  { immediate: true }
)

async function load(f) {
  loading.value = true
  mode.value = 'other'
  src.value = ''
  html.value = ''
  fallbackMsg.value = '该类型文件无法在浏览器内直接预览，请点击下载查看。'
  const ext = extOf(f.original_name)
  try {
    if (f.file_type === 'image' || ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) {
      mode.value = 'image'
      src.value = props.getUrl(f.id, true)
      return
    }
    if (f.file_type === 'pdf' || ext === 'pdf') {
      mode.value = 'pdf'
      src.value = props.getUrl(f.id, true)
      return
    }
    if (ext === 'docx') {
      const blob = await fetchBlob(f.id)
      const arrayBuffer = await blob.arrayBuffer()
      const res = await mammoth.convertToHtml({ arrayBuffer })
      html.value = res.value || '<p style="color:#909399">（文档内容为空）</p>'
      mode.value = 'html'
      return
    }
    if (ext === 'xlsx' || ext === 'xls') {
      const blob = await fetchBlob(f.id)
      const buf = await blob.arrayBuffer()
      const head = new Uint8Array(buf.slice(0, 4))
      const isZip = head[0] === 0x50 && head[1] === 0x4b // PK -> xlsx
      const isOle = head[0] === 0xd0 && head[1] === 0xcf && head[2] === 0x11 && head[3] === 0xe0 // 真 .xls(BIFF)
      let out = ''
      if (isZip) {
        const mod = await import('exceljs')
        const ExcelJS = mod.default || mod
        const wb = new ExcelJS.Workbook()
        await wb.xlsx.load(buf)
        wb.eachSheet((sheet) => {
          out += '<h3 style="margin:8px 0">' + escapeHtml(sheet.name || '') + '</h3>'
          out += '<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:13px">'
          sheet.eachRow((r, ri) => {
            out += '<tr>'
            r.eachCell({ includeEmpty: true }, (cell) => {
              const tag = ri === 1 ? 'th' : 'td'
              let v = cell.value
              if (v == null) v = ''
              else if (typeof v === 'object') v = v.text != null ? v.text : (v.result != null ? v.result : '')
              out += '<' + tag + '>' + escapeHtml(String(v)) + '</' + tag + '>'
            })
            out += '</tr>'
          })
          out += '</table><br/>'
        })
      } else if (!isOle) {
        // 非 OLE 的旧 .xls：多为 GBK 编码 Tab 文本（爱康 LIS 式），按 gbk 解码渲染
        let text
        try { text = new TextDecoder('gbk').decode(buf) } catch (e) { text = new TextDecoder('utf-8').decode(buf) }
        out = '<pre style="white-space:pre-wrap;word-break:break-all;font-size:13px">' + escapeHtml(text) + '</pre>'
      } else {
        fallbackMsg.value = '该 .xls 为旧版二进制格式，浏览器无法在线预览，请下载后查看。'
        mode.value = 'other'
        return
      }
      html.value = out || '<p style="color:#909399">（文档内容为空）</p>'
      mode.value = 'html'
      return
    }
    // doc / 其它：回退下载
    fallbackMsg.value = '该类型文件无法在浏览器内直接预览，请点击下载查看。'
    mode.value = 'other'
  } catch (e) {
    console.error(e)
    fallbackMsg.value = '预览失败：' + (e && e.message ? e.message : '该文档格式不支持，请下载后查看')
    mode.value = 'other'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.preview-html { max-height: 75vh; overflow: auto; background: #fff; padding: 4px; }
.preview-html :deep(table) { border-collapse: collapse; }
.preview-html :deep(th),
.preview-html :deep(td) { border: 1px solid #dcdfe6; padding: 4px 8px; }
.preview-html :deep(th) { background: #f5f7fa; }
.preview-html :deep(pre) { white-space: pre-wrap; word-break: break-all; }
.other-preview { text-align: center; padding: 40px; color: #888; }
.other-preview p { margin: 12px 0; }
</style>
