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
DEFAULT_MODULE_PERMISSIONS = {
    "test-items":          ["admin"],
    "documents":           ["admin", "specialty_leader"],
    "instruments":         ["admin", "specialty_leader"],
    "instrument-families": ["admin", "specialty_leader"],
    "qc":                  ["admin", "qc_manager"],
    "eqa":                 ["admin", "qc_manager"],
    "reagents":            ["admin", "reagent_manager"],
    "training":            ["admin", "training_manager"],
    "verification":        ["admin", "specialty_leader"],
    "iso15189":            ["admin", "quality_manager", "qc_manager", "training_manager", "reagent_manager", "it_manager", "specialty_leader"],
    "quality-requirements": ["admin"],
}


# 系统中所有已知模块（UI 展示用；与 frontend src/views/users/UserList.vue MODULES 对齐）
ALL_MODULES = [
    ("test-items",          "项目库"),
    ("documents",           "文件管理"),
    ("instruments",         "仪器档案"),
    ("instrument-families", "仪器关联"),
    ("qc",                  "质控管理"),
    ("eqa",                 "EQA"),
    ("reagents",            "试剂管理"),
    ("training",            "继教培训"),
    ("verification",        "性能验证"),
    ("iso15189",            "15189专项"),
    ("quality-requirements","项目质量要求"),
]


# 系统中所有已知角色（与 backend get_role_options 一致；后端 role_options.py 维护）
ALL_ROLES = [
    ("admin",            "管理员"),
    ("specialty_leader", "专业组长"),
    ("qc_manager",       "质控管理员"),
    ("reagent_manager",  "试剂管理员"),
    ("training_manager", "继教管理员"),
    ("quality_manager",  "质量负责人"),
    ("it_manager",       "信息管理员"),
    ("leader",           "组长"),
    ("member",           "职工"),
    ("director",         "主任"),
    ("deputy_director",  "副主任"),
    ("biosafety_officer","生物安全员"),
    ("staff",            "职工"),
]
