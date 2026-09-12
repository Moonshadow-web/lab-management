# -*- coding: utf-8 -*-
"""S3：crud_base 增加 group_scoped 开关（默认关=现状），并先在「项目查询」开启。"""
import io

p = 'app/core/crud_base.py'
s = io.open(p, encoding='utf-8').read()

# 1) 签名加 group_scoped
old_sig = """    delete_roles: tuple[str, ...] | None = None,
    json_fields: list[str] | None = None,
):"""
new_sig = """    delete_roles: tuple[str, ...] | None = None,
    json_fields: list[str] | None = None,
    group_scoped: bool = False,
):"""
assert old_sig in s, 'signature not found'
s = s.replace(old_sig, new_sig, 1)

# 2) 依赖与辅助
old_dep = """    _json_fields = set(json_fields or [])"""
new_dep = """    _json_fields = set(json_fields or [])
    # 专业组数据隔离：group_scoped=True 时才生效；当前组为生免组(sm)/空 → 不过滤（保持原行为）
    if group_scoped:
        from ._auth_helpers import get_current_group as _get_group

        def _group_param(group: str = Depends(_get_group)) -> str:
            return (group or "sm").strip().lower()
    else:
        def _group_param() -> str | None:
            return None

    def _need_filter(group: str | None) -> bool:
        return bool(group_scoped) and bool(group) and group not in ("sm",)

    def _shared_conds(Model_):
        \"\"\"科室共享数据：编号含 KS 段（如 BG-KS-… / MHZYY-JYK-KS-…）。\"\"\"
        out = []
        for f in ("code", "dept_no", "doc_number"):
            col = getattr(Model_, f, None)
            if col is not None:
                out.append(col.ilike("%KS%"))
        return out

    def _visible(obj, group: str) -> bool:
        \"\"\"非生免组可见：本组数据 或 KS 共享数据。\"\"\"
        if getattr(obj, "group_code", None) == group:
            return True
        for f in ("code", "dept_no", "doc_number"):
            v = getattr(obj, f, None)
            if isinstance(v, str) and "KS" in v:
                return True
        return False"""
assert old_dep in s, 'json_fields line not found'
s = s.replace(old_dep, new_dep, 1)

# 3) list_items：注入组过滤
old_list = """        params = dict(request.query_params)
        query = db.query(Model)"""
new_list = """        params = dict(request.query_params)
        query = db.query(Model)
        if _need_filter(group):
            col = getattr(Model, "group_code", None)
            if col is not None:
                query = query.filter(or_(col == group, *_shared_conds(Model)))"""
assert old_list in s
s = s.replace(old_list, new_list, 1)

# list_items 增加 group 依赖
old_list_sig = """        q: str | None = None,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        params = dict(request.query_params)"""
new_list_sig = """        q: str | None = None,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
        group: str | None = Depends(_group_param),
    ):
        params = dict(request.query_params)"""
assert old_list_sig in s
s = s.replace(old_list_sig, new_list_sig, 1)

# 4) get_item：跨组不可见 → 404
old_get = """    def get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="未找到记录")
        return _to_read(obj)"""
new_get = """    def get_item(
        item_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
        group: str | None = Depends(_group_param),
    ):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="未找到记录")
        if _need_filter(group) and not _visible(obj, group):
            raise HTTPException(status_code=404, detail="未找到记录")
        return _to_read(obj)"""
assert old_get in s
s = s.replace(old_get, new_get, 1)

# 5) create：写入当前组
old_create = """        data = item.model_dump()
        for f in _json_fields:"""
new_create = """        data = item.model_dump()
        if _need_filter(group) and hasattr(Model, "group_code"):
            data["group_code"] = group
        for f in _json_fields:"""
assert old_create in s
s = s.replace(old_create, new_create, 1)

old_create_sig = """        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
    ):
        data = item.model_dump()"""
new_create_sig = """        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
        group: str | None = Depends(_group_param),
    ):
        data = item.model_dump()"""
assert old_create_sig in s
s = s.replace(old_create_sig, new_create_sig, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('crud_base：list/get/create 组过滤已接入')

# 6) update / delete 归属校验
s = io.open(p, encoding='utf-8').read()
mark = s.index('    @router.put("/{item_id}", response_model=ReadSchema)')
seg = s[mark:]
if '无权修改其他专业组' not in seg:
    # update：签名加 group 依赖并在取到 obj 后校验
    s = s.replace("""@router.put("/{item_id}", response_model=ReadSchema)""", """@router.put("/{item_id}", response_model=ReadSchema)""", 1)
    # 在 update 函数内首个 db.get 之后插入校验（用唯一片段定位）
    import re
    m = re.search(r'(\n    def update\(\n(?:.*\n)*?        obj = db\.get\(Model, item_id\)\n)', s)
    assert m, 'update body not found'
    body = m.group(1)
    # 签名补 group 参数（在 user: User = Depends(WriteDep), 之后）
    new_body = body.replace("        user: User = Depends(WriteDep),\n", "        user: User = Depends(WriteDep),\n        group: str | None = Depends(_group_param),\n", 1)
    new_body = new_body.replace("        obj = db.get(Model, item_id)\n",
                                "        obj = db.get(Model, item_id)\n"
                                "        if _need_filter(group) and obj is not None and not _visible(obj, group):\n"
                                "            raise HTTPException(status_code=403, detail=\"无权修改其他专业组的数据\")\n", 1)
    s = s.replace(body, new_body, 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('crud_base：update 归属校验已加')
