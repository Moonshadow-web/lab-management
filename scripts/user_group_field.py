# -*- coding: utf-8 -*-
"""用户管理加「专业组」字段：后端 schema/创建接口 + 前端表单与列表列。"""
import io

# ---------------- 后端 1) schema ----------------
p = 'backend/app/schemas/__init__.py'
s = io.open(p, encoding='utf-8').read()
if 'group_code' not in s.split('class UserCreate')[0]:
    s = s.replace('''    department: str = ""
    email: str = ""
    notify_email: bool = True
    is_active: bool = True''',
'''    department: str = ""
    email: str = ""
    notify_email: bool = True
    is_active: bool = True
    group_code: str = "sm"  # 所属专业组（默认生免组）''', 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('后端 UserBase 已加 group_code')

# ---------------- 后端 2) 创建用户时写入 ----------------
p = 'backend/app/api/v1/users.py'
s = io.open(p, encoding='utf-8').read()
if 'group_code=item.group_code' not in s:
    s = s.replace('''        department=item.department,
        is_active=item.is_active,''',
'''        department=item.department,
        group_code=(item.group_code or "sm"),
        is_active=item.is_active,''', 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('创建用户已写入 group_code')

# ---------------- 前端：UserList.vue ----------------
p = 'frontend/src/views/users/UserList.vue'
s = io.open(p, encoding='utf-8').read()

# 3.1 新增表单加"专业组"
if 'addForm.group_code' not in s:
    s = s.replace('''        <el-form-item label="初始密码">
          <el-input v-model="addForm.password" placeholder="留空则默认 123456" />''',
'''        <el-form-item label="专业组">
          <el-select v-model="addForm.group_code" style="width: 100%">
            <el-option v-for="g in groupOptions" :key="g.code" :label="g.name" :value="g.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="addForm.password" placeholder="留空则默认 123456" />''', 1)
    print('新增表单已加专业组')

# 3.2 编辑表单加"专业组"
if 'editForm.group_code' not in s:
    s = s.replace('''        <el-form-item label="部门">
          <el-input v-model="editForm.department" />
        </el-form-item>''',
'''        <el-form-item label="部门">
          <el-input v-model="editForm.department" />
        </el-form-item>
        <el-form-item label="专业组">
          <el-select v-model="editForm.group_code" style="width: 100%">
            <el-option v-for="g in groupOptions" :key="g.code" :label="g.name" :value="g.code" />
          </el-select>
        </el-form-item>''', 1)
    print('编辑表单已加专业组')

# 3.3 状态：groupOptions + 表单默认值
if 'groupOptions' not in s:
    s = s.replace("const editForm = ref({ role: '', roleCodes: [], full_name: '', department: '', email: '' })",
                  "const GROUP_NAMES = { sm: '生化免疫组', lj: '临检组', wsw: '微生物组', fz: '分子组', xk: '血库' }\n"
                  "const groupOptions = ref([{ code: 'sm', name: '生化免疫组' }])\n"
                  "const editForm = ref({ role: '', roleCodes: [], full_name: '', department: '', email: '', group_code: 'sm' })", 1)
    print('状态已加 groupOptions/editForm.group_code')

# 3.4 表格加"专业组"列
if '专业组' not in s or '<el-table-column label="专业组"' not in s:
    s = s.replace('''        <el-table-column label="权限概览" min-width="200">''',
'''        <el-table-column label="专业组" width="110">
          <template #default="{ row }">{{ GROUP_NAMES[row.group_code] || '生化免疫组' }}</template>
        </el-table-column>
        <el-table-column label="权限概览" min-width="200">''', 1)
    print('表格已加专业组列')

io.open(p, 'w', encoding='utf-8').write(s)
print('UserList.vue 已更新')
