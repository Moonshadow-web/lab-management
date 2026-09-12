# -*- coding: utf-8 -*-
"""S2：登录携带专业组 + 切换组 + 组字典公开接口。"""
import io
import re

p = 'app/api/v1/auth.py'
s = io.open(p, encoding='utf-8').read()

# 1) 导入
if '_auth_helpers' not in s:
    s = s.replace(
        "from ...core.security import (",
        "from ...core._auth_helpers import (\n    DEFAULT_GROUP_CODE,\n    create_group_access_token,\n    is_admin,\n)\nfrom ...core.security import (",
        1,
    )
    s = s.replace("from ...models.user import User", "from ...models.lab_group import LAB_GROUPS, LabGroup\nfrom ...models.user import User", 1)

# 2) login 增加可选 group_code（Query），校验并签发带组令牌
old_sig = '''@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db),
):'''
new_sig = '''@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    group_code: str | None = Query(None, description="专业组编码（不传则按账号所属组）"),
    request: Request = None,
    db: Session = Depends(get_db),
):'''
assert old_sig in s, 'login signature not found'
s = s.replace(old_sig, new_sig, 1)

# 3) 账号校验通过后 → 组校验 + 带组令牌
old_tok = '''    token = create_access_token(user.id)
    refresh, jti = create_refresh_token(user.id)'''
new_tok = '''    # ===== 专业组校验（不传则用账号所属组；管理员可进任意组）=====
    user_group = (getattr(user, "group_code", "") or DEFAULT_GROUP_CODE).strip().lower()
    want = (group_code or user_group or DEFAULT_GROUP_CODE).strip().lower()
    valid = {c for c, _n, _s in LAB_GROUPS}
    if want not in valid:
        raise HTTPException(status_code=400, detail="专业组参数无效")
    if want != user_group and not is_admin(user):
        raise HTTPException(status_code=403, detail="该账号不属于所选专业组，请联系管理员")

    token = create_group_access_token(user.id, want)
    refresh, jti = create_refresh_token(user.id)'''
assert old_tok in s, 'token creation block not found'
s = s.replace(old_tok, new_tok, 1)

# 4) 返回体加当前组与可选组
old_ret = '''    return {
        "access_token": token,
        "refresh_token": refresh,
        "token_type": "bearer",
        "must_change_password": bool(user.must_change_password),
        "roles": user.roles or "",
    }'''
new_ret = '''    # 可切换的专业组：管理员=全部；普通用户=本组
    if is_admin(user):
        switchable = [c for c, _n, _s in LAB_GROUPS]
    else:
        switchable = [user_group]

    return {
        "access_token": token,
        "refresh_token": refresh,
        "token_type": "bearer",
        "must_change_password": bool(user.must_change_password),
        "roles": user.roles or "",
        "group_code": want,
        "can_switch_group": is_admin(user),
        "switchable_groups": switchable,
    }


@router.get("/lab-groups")
def list_lab_groups(db: Session = Depends(get_db)):
    """专业组字典（免登录，供登录页选择）。数据库无数据时回退内置常量。"""
    rows = db.query(LabGroup).order_by(LabGroup.sort_no).all()
    if rows:
        return {"items": [{"code": g.code, "name": g.name} for g in rows if g.is_active]}
    return {"items": [{"code": c, "name": n} for c, n, _s in LAB_GROUPS]}


@router.post("/switch-group")
def switch_group(
    group_code: str = Query(..., description="目标专业组编码"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """切换当前专业组（管理员可为任意组；普通用户仅限本组），返回新的 access token。"""
    valid = {c for c, _n, _s in LAB_GROUPS}
    want = (group_code or "").strip().lower()
    if want not in valid:
        raise HTTPException(status_code=400, detail="专业组参数无效")
    user_group = (getattr(user, "group_code", "") or DEFAULT_GROUP_CODE).strip().lower()
    if want != user_group and not is_admin(user):
        raise HTTPException(status_code=403, detail="无权切换到该专业组")
    return {
        "access_token": create_group_access_token(user.id, want),
        "token_type": "bearer",
        "group_code": want,
    }'''
assert old_ret in s, 'login return block not found'
s = s.replace(old_ret, new_ret, 1)

# 5) Query 导入
if 'Query' not in s.split('\n\n')[0] and 'from fastapi import' in s:
    s = re.sub(r'from fastapi import ([^\n]+)', lambda m: m.group(0) if 'Query' in m.group(1) else 'from fastapi import ' + m.group(1) + ', Query', s, count=1)

io.open(p, 'w', encoding='utf-8').write(s)
print('auth.py 已更新')
