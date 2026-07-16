<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="login-title">生免组实验室管理系统</div>
      <div class="login-sub">民航总医院检验科 · 生化免疫专业组</div>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" style="width: 100%" @click="onSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>

    <!-- 首次登录强制改密弹窗 -->
    <el-dialog
      v-model="showChangePwd"
      title="首次登录 · 请修改初始密码"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      align-center
    >
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        安全要求：首次登录必须修改初始密码后方可使用系统。
      </el-alert>
      <el-form :model="pwdForm" label-width="90px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="至少8位，含字母和数字" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password @keyup.enter="onChangePwd" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="changing" @click="onChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)

// 强制改密
const showChangePwd = ref(false)
const changing = ref(false)
const pwdForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })

async function onSubmit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const resp = await auth.login(form.value.username, form.value.password)
    if (resp.must_change_password) {
      // 预填原密码（初始密码 123456）
      pwdForm.value.oldPassword = form.value.password
      pwdForm.value.newPassword = ''
      pwdForm.value.confirmPassword = ''
      showChangePwd.value = true
      ElMessage.info('首次登录，请先修改初始密码')
    } else {
      ElMessage.success('登录成功')
      router.push('/dashboard')
    }
  } catch (e) {
    const detail = e?.response?.data?.detail
    ElMessage.error(detail || '登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}

async function onChangePwd() {
  const { oldPassword, newPassword, confirmPassword } = pwdForm.value
  if (!oldPassword || !newPassword || !confirmPassword) {
    ElMessage.warning('请填写完整')
    return
  }
  if (newPassword !== confirmPassword) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (newPassword.length < 8 || !(/\d/.test(newPassword) && /[a-zA-Z]/.test(newPassword))) {
    ElMessage.error('新密码至少 8 位，且需同时包含字母和数字')
    return
  }
  changing.value = true
  try {
    await auth.changePassword(oldPassword, newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    showChangePwd.value = false
    // 改密成功后退出登录态，让用户用新密码重新登录
    auth.logout()
    form.value.password = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '修改失败，请检查原密码')
  } finally {
    changing.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a365d 0%, #2c4a73 100%);
}
.login-card {
  width: 380px;
  padding: 10px 20px;
}
.login-title {
  font-size: 22px;
  font-weight: 700;
  text-align: center;
  color: #1a365d;
}
.login-sub {
  text-align: center;
  color: #888;
  margin-bottom: 20px;
  font-size: 13px;
}
</style>
