"""生免组人员账号种子：一次性落库 18 个账号（初始密码 123456、首次登录强制改密）。

角色采用「粗粒度 role + 详细 roles」双字段：
- role: admin / leader / member（兼容既有权限与通知判断）
- roles: 详细组织角色码，逗号分隔，可兼任（如吕文娟=质控管理员+继教管理员）

幂等：用户名已存在时仅同步姓名/角色，不覆盖密码与 must_change_password，
避免重复执行把已改密用户重置回初始密码。
"""
from ..core.security import hash_password
from ..models.user import User

# (用户名, 姓名, 粗粒度role, 详细roles逗号分隔)
USERS = [
    ("jinzizheng", "金子铮", "admin", "admin,specialty_leader"),
    ("yangjing", "杨静", "leader", "specialty_leader"),
    ("wangchunxin", "王春馨", "member", "staff"),
    ("zhaohaiyuan", "赵海元", "member", "it_manager"),
    ("xialijiao", "夏立娇", "member", "reagent_manager"),
    ("zhuchunyang", "朱春阳", "member", "qc_manager"),
    ("yaojianmin", "姚建民", "member", "staff"),
    ("wangxuejing", "王学晶", "leader", "director"),
    ("zhengfei", "郑飞", "member", "reagent_manager"),
    ("qindongfang", "秦东芳", "member", "reagent_manager"),
    ("zhangchanyuan", "张婵媛", "leader", "quality_manager"),
    ("kongyalong", "孔亚龙", "member", "it_manager"),
    ("qinmanhong", "秦满红", "member", "staff"),
    ("lvwenjuan", "吕文娟", "member", "qc_manager,training_manager"),
    ("lidong", "李东", "leader", "deputy_director"),
    ("zhaorui", "赵瑞", "member", "staff"),
    ("wangshuhua", "王淑华", "member", "staff"),
    ("xuxiaolin", "徐晓琳", "member", "biosafety_officer"),
]


def seed_users(db):
    for username, full_name, role, roles in USERS:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            # 已存在：仅同步组织信息，保留密码与改密状态
            existing.full_name = full_name
            existing.role = role
            existing.roles = roles
            continue
        db.add(
            User(
                username=username,
                full_name=full_name,
                role=role,
                roles=roles,
                department="生免组",
                password_hash=hash_password("123456"),
                must_change_password=True,
                is_active=True,
            )
        )
    db.commit()
