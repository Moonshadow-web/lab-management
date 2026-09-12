# -*- coding: utf-8 -*-
"""S2 前端：登录页选专业组 + 顶栏显示/切换专业组。"""
import io

# ---------------- 1) store/auth.js：login 带组 + 组状态/切换 ----------------
p = 'frontend/src/store/auth.js'
s = io.open(p, encoding='utf-8').read()

old = """    async login(username, password) {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const data = await request.post('/api/v1/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })"""
new = """    async login(username, password, groupCode) {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const q = groupCode ? `?group_code=${encodeURIComponent(groupCode)}` : ''
      const data = await request.post('/api/v1/auth/login' + q, form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      // 当前专业组（老后端不返回时默认生免组）
      this.groupCode = data.group_code || 'sm'
      localStorage.setItem('group_code', this.groupCode)
      this.canSwitchGroup = !!data.can_switch_group
      this.switchableGroups = data.switchable_groups || [this.groupCode]"""
assert old in s, 'auth.js login not found'
s = s.replace(old, new, 1)

# 状态字段
old_state = """    token: localStorage.getItem('token') || '',"""
new_state = """    token: localStorage.getItem('token') || '',
    groupCode: localStorage.getItem('group_code') || 'sm',
    canSwitchGroup: false,
    switchableGroups: [],"""
assert old_state in s
s = s.replace(old_state, new_state, 1)

# actions 增加 switchGroup / groupNameOf
old_logout = "    logout() {"
new_logout = """    // 切换专业组：换新令牌后强制刷新，避免残留上一组数据
    async switchGroup(code) {
      const data = await request.post(`/api/v1/auth/switch-group?group_code=${encodeURIComponent(code)}`)
      this.token = data.access_token
      localStorage.setItem('token', this.token)
      this.groupCode = data.group_code || code
      localStorage.setItem('group_code', this.groupCode)
      location.reload()
    },
    logout() {"""
if 'switchGroup' not in s:
    s = s.replace(old_logout, new_logout, 1)

# getters：组名
old_getter = "  getters: {"
new_getter = """  getters: {
    groupName() {
      const map = { sm: '生化免疫组', lj: '临检组', wsw: '微生物组', fz: '分子组', xk: '血库' }
      return map[this.groupCode] || this.groupCode || '生化免疫组'
    },"""
if 'groupName' not in s:
    s = s.replace(old_getter, new_getter, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('store/auth.js 已更新')

# ---------------- 2) Login.vue：专业组下拉 ----------------
p = 'frontend/src/views/Login.vue'
s = io.open(p, encoding='utf-8').read()
if '专业组' not in s:
    s = s.replace("""        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" size="large" />""",
"""        <el-form-item>
          <el-select v-model="form.groupCode" size="large" style="width:100%" placeholder="选择专业组">
            <el-option v-for="g in groups" :key="g.code" :label="g.name" :value="g.code" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" size="large" />""", 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('Login.vue 模板已加专业组下拉')

# 逻辑：加载组字典 + 提交带组
import re
s = io.open(p, encoding='utf-8').read()
if 'groups' not in s.split('const form')[0]:
    # form 增加 groupCode
    s = re.sub(r"(const form = reactive\(\{)(\s*)", lambda m: m.group(1) + "\n  groupCode: localStorage.getItem('group_code') || 'sm',", s, count=1)
    # 引入 ref/onMounted（若缺）
    if 'onMounted' not in s:
        s = s.replace("import { reactive, ref } from 'vue'", "import { reactive, ref, onMounted } from 'vue'", 1)
        if 'onMounted' not in s:
            s = s.replace("import { reactive } from 'vue'", "import { reactive, ref, onMounted } from 'vue'", 1)
    # 组字典与加载
    s = s.replace("const loading = ref(false)", """const loading = ref(false)
const groups = ref([{ code: 'sm', name: '生化免疫组' }])

onMounted(async () => {
  try {
    const res = await request.get('/api/v1/auth/lab-groups')
    if (res?.items?.length) {
      groups.value = res.items
      if (!groups.value.some((g) => g.code === form.groupCode)) form.groupCode = groups.value[0].code
    }
  } catch (e) { /* 拉不到就用默认生免组 */ }
})""", 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('Login.vue 逻辑已加组字典')

# 提交时带组
s = io.open(p, encoding='utf-8').read()
s = s.replace("await auth.login(form.username, form.password)", "await auth.login(form.username, form.password, form.groupCode)", 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('Login.vue 提交已带专业组')

# ---------------- 3) AppLayout：顶栏显示 + 切换 ----------------
p = 'frontend/src/layout/AppLayout.vue'
s = io.open(p, encoding='utf-8').read()
if 'groupName' not in s:
    s = s.replace("""        <span class="title">{{ currentTitle }}</span>""",
"""        <span class="title">{{ currentTitle }}</span>
        <el-tag size="small" type="info" style="margin-left:8px;">{{ auth.groupName }}</el-tag>
        <el-select
          v-if="auth.canSwitchGroup"
          v-model="switchTarget"
          size="small"
          style="width:120px;margin-left:8px;"
          @change="onSwitchGroup"
        >
          <el-option v-for="c in auth.switchableGroups" :key="c" :label="GROUP_NAMES[c] || c" :value="c" />
        </el-select>""", 1)
    s = s.replace("import { Share, Connection, Document, Menu, Close, Grid } from '@element-plus/icons-vue'",
"""import { Share, Connection, Document, Menu, Close, Grid } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'""", 1)
    # 脚本逻辑
    s = s.replace("const drawerVisible = ref(false)", """const drawerVisible = ref(false)
const GROUP_NAMES = { sm: '生化免疫组', lj: '临检组', wsw: '微生物组', fz: '分子组', xk: '血库' }
const switchTarget = ref(auth.groupCode || 'sm')
async function onSwitchGroup(code) {
  if (!code || code === auth.groupCode) return
  try {
    await auth.switchGroup(code)
  } catch (e) {
    ElMessage.error('切换失败：' + (e?.response?.data?.detail || e.message))
    switchTarget.value = auth.groupCode
  }
}""", 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('AppLayout 顶栏已加组显示与切换')
