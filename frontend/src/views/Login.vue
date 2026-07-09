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
      <div class="login-tip">默认管理员账号：admin / admin123</div>
    </el-card>
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

async function onSubmit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error('登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
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
.login-tip {
  text-align: center;
  color: #aaa;
  font-size: 12px;
  margin-top: 14px;
}
</style>
