# 前端代码库组织模式探索报告 — 用于指导「试剂管理」View 开发

## 1. 路由配置 `frontend/src/router/index.js`

### 关键位置
- **文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\router\index.js`
- 路由定义为一个 `routes` 数组，传给 `createRouter`。
- 登录页是独立路由（`meta: { public: true }`），无需鉴权。
- 所有业务页面作为 `/` 路由的子路由，使用 `AppLayout` 作为父组件（提供侧边栏 + 顶栏）。

### 添加新路由的方式
在 `routes[1].children` 数组中追加一项：
```js
{
  path: 'reagents',           // URL 路径
  name: 'reagents',           // 路由名称
  component: () => import('../views/reagents/ReagentList.vue'),  // 懒加载组件
  meta: { title: '试剂管理', moduleKey: 'reagents' },           // 标题 + 权限键
}
```

### meta 字段说明
- `title`: 页面标题，显示在顶栏
- `moduleKey`: 权限标识 key，用于菜单过滤和 `canWrite` 权限判定
- `moduleKeys`（数组形式）: 用于聚合菜单（如质控管理），任一 key 有权限即可见
- `adminOnly`: 设为 `true` 表示仅管理员可访问（路由守卫会检查）

### 路由守卫
`router.beforeEach` 处理三层逻辑：
1. 是否登录（除 `public` 路由外均需登录）
2. 是否 adminOnly 路由（仅管理员可访问）
3. 模块级守卫（`technical_support` 角色严格收口，通过 `auth.canAccessAnyMenu()` 判定）

---

## 2. 菜单/侧边栏配置 `frontend/src/layout/AppLayout.vue`

### 关键位置
- **文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\layout\AppLayout.vue`

### 菜单定义方式（`computed menus` 内）
```js
const all = [
  { path: '/dashboard', title: '工作台', icon: 'Odometer' },
  { path: '/reagents', title: '试剂管理', icon: 'ShoppingCart', moduleKey: 'reagents' },
  // ...
]
```

### 权限过滤
- 对 `technical_support` 角色：严格按 `moduleKey`/`moduleKeys` 授权过滤
- 对 admin：额外显示用户管理、权限配置、审计日志、提醒设置四个管理项

### 添加菜单项
在 `all` 数组追加与路由对应的菜单配置；即可自动渲染。

### 侧边栏底部附加按钮
`aside-footer` 区域可配置快捷导航按钮（如"项目库与质评关联"、"仪器关联管理"等），通过 `auth.canAccessMenu()` 控制显示。

---

## 3. API 调用层 `frontend/src/api/`

### 关键文件
- **请求实例**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\utils\request.js`
  - 基于 `axios` 创建，`baseURL: '/'`，超时 15 秒
  - 请求拦截器：自动注入 `Bearer <token>` 到 `Authorization` 头
  - 响应拦截器：自动解包 `response.data`；401 自动用 refresh token 续期（带并发队列锁）

### API 模块规范（以 reagents 为例）
**文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\api\reagents.js`
```js
import request from '../utils/request'

export function listReagents(params) {
  return request.get('/api/v1/reagents', { params })
}
export function createReagent(data) {
  return request.post('/api/v1/reagents', data)
}
export function updateReagent(id, data) {
  return request.put(`/api/v1/reagents/${id}`, data)
}
export function deleteReagent(id) {
  return request.delete(`/api/v1/reagents/${id}`)
}
```

### 模式
- 每个 API 模块导出函数，函数内调用 `request.get/post/put/delete`
- 后端路径统一为 `/api/v1/{资源名}`
- 列表接口接收 `{ page, page_size, q, ... }` 参数，返回 `{ items, total }` 结构
- `request` 自动返回 `response.data`，所以调用方直接拿到后端 JSON 数据体

---

## 4. 视图组件模式

### 模式 A：直接使用 `CrudTable` 组件（推荐 — 最简洁）
**代表文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\views\reagents\ReagentList.vue`

这是最简洁标准的 CRUD 视图模式。template 仅包含：
```vue
<template>
  <div class="page">
    <CrudTable ref="crud" :columns="columns" :fetch="fetch"
      search-placeholder="搜索名称 / 批号 / 厂家 / 供应商..."
      :show-add="auth.canWrite('reagents')"
      :can-write="auth.canWrite('reagents')"
      @add="onAdd" @edit="onEdit" @delete="onDelete"
    />
    <EditDialog v-model="dialogVisible" :title="editingId ? '编辑试剂' : '新增试剂'"
      :form="form" :fields="fields" :rules="rules"
      :submitting="submitting" @submit="onSubmit"
    />
  </div>
</template>
```

#### CrudTable 组件 `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\components\CrudTable.vue`
- Props: `columns`, `fetch`, `searchPlaceholder`, `showAdd`, `canWrite`, `actionWidth`, `extraParams`
- Emits: `add`, `edit`, `delete`
- 内部管理：搜索关键字 `q`、分页 `page`/`pageSize`、`total`、`loading`
- 自动在 `onMounted` 时调用 `fetch` 加载数据
- 暴露 `refresh()` 方法供父组件调用
- 表格 + 分页全部内置；操作列固定右侧

#### EditDialog 组件 `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\components\EditDialog.vue`
- Props: `modelValue` (v-model), `title`, `form`, `fields`, `rules`, `submitting`
- Emits: `update:modelValue`, `submit`
- 支持字段类型：`text`（默认）、`textarea`、`select`、`switch`、`date`
- 提交前做 `el-form` 校验，通过后 emit `submit`

### 模式 B：手写 template 控制（更灵活）
**代表文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\views\quality\QualityRequirementList.vue`

适合复杂页面（多标签页、矩阵视图、自定义操作按钮）。不使用 CrudTable，而是：
- 手写 `el-table` + `el-pagination`
- 自行管理所有 loading/error/empty 状态
- 调用 API 函数直接填充表格数据

### script setup 模式
- 使用 `<script setup>` + Composition API
- `ref()` 用于响应式值，`reactive()` 用于对象
- `onMounted` 中加载初始数据
- `ElMessage.success()` / `ElMessage.error()` 提示操作结果
- `ElMessageBox.confirm()` 做删除确认

### 后端 API 响应错误处理
所有 API catch 块均使用统一错误提取模式：
```js
e?.response?.data?.detail || e.message
```

---

## 5. Store 模式

### Auth Store
**文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\store\auth.js`
- 使用 `Pinia` 的 `defineStore('auth', { ... })`
- State: `token`, `refreshToken`, `user`（均持久化到 localStorage）
- Getters: `isLoggedIn`, `myRoles`, `isAdmin`, `isTechnicalSupport`
- Actions:
  - `login()` — 登录后保存 token，拉用户信息
  - `logout()` — 清除 token 并跳转
  - `canWrite(moduleKey)` — 判断当前用户对某模块是否有写权限（优先读 permission store，回退硬编码 fallback）
  - `canDelete(moduleKey)` — 判断删除权限
  - `canAccessMenu(moduleKey)` — 判断菜单可见性
  - `canAccessAnyMenu(keys)` — 聚合菜单可见性

### 在视图中的使用方式
```js
import { useAuthStore } from '../../store/auth'
const auth = useAuthStore()
// 用法：auth.canWrite('reagents')、auth.canAccessMenu('reagents')
```

### Permission Store
**文件**: `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\store\permission.js`
- 登录后从后端拉 `moduleRoles` 映射（模块 key -> 允许角色列表）
- 提供 `canWrite`, `canDelete`, `canAccess`, `canAccessAny` 等方法
- 前端硬编码 fallback 数据保证后端未返回时正常工作

---

## 6. 总结 —— 开发「试剂管理」新模块需要的操作清单

### 如果 ReagentList.vue 已存在且需要增强：
修改 `d:\workbuddyprojects\网页版-生免速查工具\frontend\src\views\reagents\ReagentList.vue`
- 利用 `CrudTable` 和 `EditDialog` 两个通用组件
- 只需提供 `columns`, `fields`, `rules`, `fetch` 函数即可
- 权限控制：`auth.canWrite('reagents')`

### 如果添加全新模块：

| 步骤 | 操作 | 参考文件 |
|------|------|----------|
| 1. 创建 API 模块 | `frontend/src/api/reagents.js` | `qualityRequirements.js` |
| 2. 创建视图组件 | `frontend/src/views/reagents/ReagentList.vue` | `QualityRequirementList.vue` 或 `ReagentList.vue` |
| 3. 注册路由 | `frontend/src/router/index.js` 的 children 中追加 | 第 26 行试剂管理示例 |
| 4. 添加菜单项 | `frontend/src/layout/AppLayout.vue` 的 `menus` 计算属性中追加 | 第 74 行试剂管理示例 |
| 5. 配置权限 | `frontend/src/store/auth.js` 的 `FALLBACK_MODULE_WRITE_ROLES` 中加角色映射 | 第 22-23 行 `reagents` 示例 |

### 关键组件引用路径
```
CrudTable:  frontend/src/components/CrudTable.vue
EditDialog: frontend/src/components/EditDialog.vue
request:    frontend/src/utils/request.js
```
