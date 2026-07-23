"""模块写权限配置：哪个角色可以写哪个模块。

源数据原来硬编码在 frontend/src/store/auth.js 的 MODULE_WRITE_ROLES。
本表 + 启动种子把硬编码值搬到数据库，admin 可在 UI 改并立即生效。

数据模型：一行 = (module_key, role_code) 一对授权。
未出现在表里的 (module, role) 组合 = 未授权。
admin 是通杀角色：canWrite 逻辑里 admin 短路，不读本表。
"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ModulePermission(Base):
    """(module_key, role_code) 一行 = 该角色被允许写该模块。"""

    __tablename__ = "module_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(64), index=True)
    role_code: Mapped[str] = mapped_column(String(64), index=True)
    updated_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 启动种子：与旧硬编码 MODULE_WRITE_ROLES 完全一致，作为"出厂默认"。
# 已有的人工配置不会被覆盖（seed 只在表为空时灌入）。
#
# 模块命名约定：
#   - 普通模块：xxx           write 权限
#   - 删除专属：xxx_delete      delete 权限（不显式声明时与 write 相同）
#   - 编辑既有：xxx_edit       用于 comparison/interlab 的"既有计划编辑"
DEFAULT_MODULE_PERMISSIONS = {
    "test-items":          ["admin"],
    "documents":           ["admin", "specialty_leader"],
    "instruments":         ["admin", "specialty_leader"],
    "instrument-families": ["admin", "specialty_leader"],
    "qc-monthly":          ["admin", "qc_manager", "member", "staff"],
    "qc-monthly_delete":   ["admin", "qc_manager"],
    "qc-target":           ["admin", "qc_manager", "member", "staff"],
    "qc-target_delete":    ["admin", "qc_manager"],
    "eqa":                 ["admin", "qc_manager"],
    "eqa_delete":          ["admin", "qc_manager"],
    # comparison / interlab：查看(access)对职工(member/staff)开放，只读；
    # 新建/录入/上传 用 *-create（admin/qc_manager/technical_support）；
    # 编辑/删除/生成报告 用 *-edit（admin/qc_manager）。
    "comparison":          ["admin", "qc_manager", "technical_support", "member", "staff"],
    "comparison-create":   ["admin", "qc_manager", "technical_support"],
    "comparison-edit":     ["admin", "qc_manager"],
    "interlab":            ["admin", "qc_manager", "technical_support", "member", "staff"],
    "interlab-create":     ["admin", "qc_manager", "technical_support"],
    "interlab-edit":       ["admin", "qc_manager"],
    "reagents":            ["admin", "reagent_manager"],
    "reagents_delete":     ["admin", "reagent_manager"],
    "training":            ["admin", "training_manager"],
    "training_delete":     ["admin", "training_manager"],
    "verification":        ["admin", "specialty_leader"],
    "iso15189":            ["admin", "quality_manager", "qc_manager", "training_manager", "reagent_manager", "it_manager", "specialty_leader"],
    "quality-requirements": ["admin"],
    "scheduling":          ["admin", "specialty_leader"],
}


# 系统中所有已知模块（UI 展示用；与 frontend src/views/users/UserList.vue MODULES 对齐）
ALL_MODULES = [
    ("test-items",          "项目库"),
    ("documents",           "文件管理"),
    ("instruments",         "仪器档案"),
    ("instrument-families", "仪器关联"),
    ("qc-monthly",          "室内质控月结"),
    ("qc-target",           "质控品靶值"),
    ("eqa",                 "EQA"),
    ("comparison",          "仪器间比对（查看）"),
    ("comparison-create",   "仪器间比对（新建/录入）"),
    ("comparison-edit",     "仪器间比对（编辑既有）"),
    ("interlab",            "室间比对（查看）"),
    ("interlab-create",     "室间比对（新建/录入）"),
    ("interlab-edit",       "室间比对（编辑既有）"),
    ("reagents",            "试剂管理"),
    ("training",            "继教培训"),
    ("verification",        "性能验证"),
    ("iso15189",            "15189专项"),
    ("quality-requirements","项目质量要求"),
    ("scheduling",          "排班管理"),
]


# 系统中所有已知角色
# 注意：technical_support 仅供"权限配置"页和后端 canWrite 识别，
# 不出现在 users.py 的 ROLE_OPTIONS 下拉里（不通过 UI 增删，只手动写库）。
ALL_ROLES = [
    ("admin",             "管理员"),
    ("specialty_leader",  "专业组长"),
    ("qc_manager",        "质控管理员"),
    ("reagent_manager",   "试剂管理员"),
    ("training_manager",  "继教管理员"),
    ("quality_manager",   "质量负责人"),
    ("it_manager",        "信息管理员"),
    ("leader",            "组长"),
    ("member",            "职工"),
    ("director",          "主任"),
    ("deputy_director",   "副主任"),
    ("biosafety_officer", "生物安全员"),
    ("staff",             "职工"),
    ("technical_support", "技术支持"),
]
