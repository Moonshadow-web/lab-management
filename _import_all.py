import os, sys, json, openpyxl, urllib.request, urllib.parse

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
DESKTOP = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
DATE = "2026-06-09"
PUSH = "--push" in sys.argv

def req(method, path, tok=None, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if tok: h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, (resp.read() if raw else json.loads(resp.read()))
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500].decode(errors="replace")

def fnum(v):
    if v is None: return None
    try: return float(v)
    except: return None

# ---------- 名称映射 ----------
SHENG_MAP = {  # Excel缩写 -> 分组项目名
 'ALB':'Alb','ALP':'ALP','ALT':'ALT','AMY':'AMY','AST':'AST','BUN':'UREA','CA':'Ca','CHE':'CHE',
 'CHOL':'TC','CK':'CK','CL':'CL','CO2':'CO2','CRE':'Cr','CYSC':'CysC','FE':'Fe','DBIL':'DBiL',
 'GGT':'GGT','GLU':'GlU','HCY':'HCY','HDL':'HDL','K':'K','LDH':'LDH','LDL':'LDL','LPS':'LPS',
 'Mg':'Mg','NA':'Na','P':'P','PA':'PA','TBA':'TBA','TBIL':'TBiL','TG':'TG','TP':'TP','UA':'UA','UIBC':'UIBC'}
DXI_MAP = {'FER':'FERR','FOLW':'叶酸','B12':'B12','hsTnI':'cTnI','MYO':'MYO','BNP':'BNP','CKMB':'CK-MB','IFAb':'IFA','sTfR':'sTfR','IL-6':'IL-6','PCT':'PCT'}
ZAO_MAP = {'HCG':'β-HCG','孕酮':'Prog','雌二醇':'E2'}

def norm(name, mp):
    return mp.get(name.strip())

# ---------- 解析 生化 (主表, 3水平, 横向分块) ----------
def parse_sheng():
    wb = openpyxl.load_workbook(os.path.join(DESKTOP, "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx"), data_only=True)
    ws = wb["生化分析仪比对"]
    rows = {}
    te_map = {}
    # 三个水平块起始列: 1, 10, 19 (每块9列)
    for blk, base in enumerate((1, 10, 19)):
        lv = blk + 1
        for rr in range(5, 113):
            item_raw = ws.cell(row=rr, column=base).value  # col1 of block = item (None for non-item rows)
            if item_raw is None: continue
            item_raw = str(item_raw).strip()
            if item_raw in ('水平4','水平5'): continue
            name = norm(item_raw, SHENG_MAP)
            if not name:
                print("  [生化] 未匹配:", item_raw); continue
            ref = fnum(ws.cell(row=rr, column=base+1).value)   # AU5821-B
            a = fnum(ws.cell(row=rr, column=base+3).value)      # AU5821-A
            jz = fnum(ws.cell(row=rr, column=base+6).value)     # 5811-急诊
            te = ws.cell(row=rr, column=base+2).value            # 允许TE%
            rows.setdefault((name, lv), {"ref": ref, "values": {}})
            rows[(name, lv)]["ref"] = ref
            rows[(name, lv)]["values"]["67"] = a   # AU5821-A
            rows[(name, lv)]["values"]["5"] = jz   # 5811-急诊
            te_map[name] = str(te)
    return rows, te_map

# ---------- 解析 DXI800 (纵向分块, 5水平) ----------
def parse_dxi():
    wb = openpyxl.load_workbook(os.path.join(DESKTOP, "BG-SM-CZ-024-定量室内比对结果记录分析表（DXI800分析仪）.xlsx"), data_only=True)
    ws = wb.active
    rows = {}
    block_ref = 71  # 当前块参比机: 71=DXI800-3, 72=DXI800-4
    for rr in range(1, ws.max_row + 1):
        c1 = ws.cell(row=rr, column=1).value
        c2 = ws.cell(row=rr, column=2).value
        if c1 == '水平' and c2 == '项目':
            h3 = str(ws.cell(row=rr, column=3).value or "")
            block_ref = 72 if '4' in h3 else 71
            continue
        if c1 in ('汇总', None) or c2 is None:
            continue
        if not isinstance(c1, (int, float)):  # 数据行 c1=水平int
            continue
        lv = int(c1); item_raw = str(c2).strip()
        name = norm(item_raw, DXI_MAP)
        if not name:
            print("  [DXI] 未匹配:", item_raw); continue
        ref_v = fnum(ws.cell(row=rr, column=3).value)
        cmp_v = fnum(ws.cell(row=rr, column=5).value)
        # 叶酸急诊列占位0 -> 用偏倚%反算
        if name == '叶酸' and cmp_v == 0:
            bias = fnum(ws.cell(row=rr, column=6).value)
            if bias is not None and ref_v is not None:
                cmp_v = round(ref_v * (1 + bias), 4)
        ent = rows.setdefault((name, lv), {"ref": None, "values": {}})
        if block_ref == 71:
            ent["ref"] = ref_v  # 主参比 DXI800-3
        else:
            ent["values"]["72"] = ref_v  # DXI800-4 作为额外比对
        ent["values"]["73"] = cmp_v  # DXI800-急诊
    return rows

# ---------- 解析 早孕 (纵向分块, 5水平) ----------
def parse_zao():
    wb = openpyxl.load_workbook(os.path.join(DESKTOP, "BG-SM-CZ-027-定量室内比对结果记录分析表（早孕系列）.xlsx"), data_only=True)
    ws = wb.active
    rows = {}
    for rr in range(1, ws.max_row + 1):
        c1 = ws.cell(row=rr, column=1).value
        if str(c1 or "").startswith('水平') and ws.cell(row=rr, column=2).value is None:
            continue  # 水平N 分隔行
        c2 = ws.cell(row=rr, column=2).value
        if c2 in ('DXI800唐筛','DXI800急诊','允许TE%','偏倚%','是否允许Y/N') or c1 in ('汇总',):
            continue
        if c1 is None or str(c1).strip() in ('',):
            continue
        item_raw = str(c1).strip()
        name = norm(item_raw, ZAO_MAP)
        if not name:
            print("  [早孕] 未匹配:", item_raw); continue
        ref_v = fnum(ws.cell(row=rr, column=2).value)   # DXI800唐筛
        cmp_v = fnum(ws.cell(row=rr, column=4).value)   # DXI800急诊
        lv = int(str(c1).replace('水平','').strip()) if str(c1).startswith('水平') else None
        # 早孕数据行: c1=项目名(非水平), 但需定位水平->用上一个分隔行的水平
        # 简化: 早孕每行 c1=项目名, 通过累计水平索引
        rows.setdefault("__lv", 0)
        ent = rows.setdefault((name, rows.get("__cur_lv")), {"ref": ref_v, "values": {}})
        ent["ref"] = ref_v
        ent["values"]["73"] = cmp_v
    return rows

# 早孕需要按水平分块解析
def parse_zao2():
    wb = openpyxl.load_workbook(os.path.join(DESKTOP, "BG-SM-CZ-027-定量室内比对结果记录分析表（早孕系列）.xlsx"), data_only=True)
    ws = wb.active
    rows = {}
    cur_lv = None
    for rr in range(1, ws.max_row + 1):
        c1 = ws.cell(row=rr, column=1).value
        c2 = ws.cell(row=rr, column=2).value
        if str(c1 or "").startswith('水平') and c2 is None:
            try: cur_lv = int(str(c1).replace('水平','').strip())
            except: cur_lv = None
            continue
        if c2 in ('DXI800唐筛','DXI800急诊','允许TE%','偏倚%','是否允许Y/N') or str(c1 or '') in ('汇总',):
            continue
        if c1 is None or cur_lv is None: continue
        item_raw = str(c1).strip()
        name = norm(item_raw, ZAO_MAP)
        if not name:
            print("  [早孕] 未匹配:", item_raw); continue
        ref_v = fnum(c2)
        cmp_v = fnum(ws.cell(row=rr, column=4).value)
        rows[(name, cur_lv)] = {"ref": ref_v, "values": {"73": cmp_v}}
    return rows

if __name__ == "__main__":
    # 登录
    r = urllib.request.Request(BASE + "/auth/login", data=urllib.parse.urlencode({"username":"jinzizheng","password":"Jzz6827556"}).encode(), headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
    TOK = json.loads(urllib.request.urlopen(r, timeout=30).read())["access_token"]

    # 校验仪器 id
    st, insts = req("GET", "/comparison/groups/1", TOK)  # 借用分组接口不行, 用 instruments
    # 直接取 instruments
    st, inst_list = req("GET", "/instruments?page_size=100", TOK)
    idname = {i["id"]: i["name"] for i in inst_list.get("items", inst_list) if isinstance(i, dict)}
    for iid in (5, 67, 68, 69, 71, 72, 73, 74):
        print(f"  仪器 id={iid} -> {idname.get(iid,'??')}")

    sheng, sheng_te = parse_sheng()
    dxi = parse_dxi()
    zao = parse_zao2()
    print(f"\n[解析结果] 生化 {len(sheng)} 行, DXI800 {len(dxi)} 行, 早孕 {len(zao)} 行")
    print("  生化 items:", sorted({k[0] for k in sheng}))
    print("  DXI items:", sorted({k[0] for k in dxi}))
    print("  早孕 items:", sorted({k[0] for k in zao}))
    print("  生化 TE样例:", {k: sheng_te[k] for k in list(sheng_te)[:5]})

    if not PUSH:
        print("\n*** DRY-RUN 完成（未推送）。加 --push 执行写入。 ***")
        sys.exit(0)

    # ===== 以下为推送 =====
    print("\n>>> PUSH 模式：开始写入...")
    # 1. 修正分组配置
    # 生化(group1): ref=68(AU5821-B), levels=3
    req("PUT", "/comparison/groups/1", TOK, {"reference_instrument_id": 68, "levels": 3, "instrument_ids": [67,68,5]})
    # DXI800(group2): ref=71, insts=[69,71,72,73]
    st, g2 = req("GET", "/comparison/groups/2", TOK)
    items2 = g2["items"]
    for it in items2:
        if it["name"] == "IL-6": it["instrument_ids"] = [69, 73]
        elif it["name"] == "CK-MB": it["instrument_ids"] = [71, 72, 73]
        else: it["instrument_ids"] = []
    req("PUT", "/comparison/groups/2", TOK, {"reference_instrument_id": 71, "levels": 5, "instrument_ids": [69,71,72,73], "items": items2})
    # 早孕(group4): ref=74, insts=[74,73], te=0.125
    st, g4 = req("GET", "/comparison/groups/4", TOK)
    items4 = g4["items"]
    for it in items4:
        it["te"] = "0.125"; it["instrument_ids"] = []
    req("PUT", "/comparison/groups/4", TOK, {"reference_instrument_id": 74, "levels": 5, "instrument_ids": [74,73], "items": items4})
    print("  分组配置已更新")

    # 2. 删除现有 2026 H1 计划 (groups 1,2,4)
    st, pls = req("GET", "/comparison/plans?page_size=200", TOK)
    for p in pls["items"]:
        if p["group_id"] in (1,2,4) and p["year"]==2026 and p["half"]==1:
            req("DELETE", f"/comparison/plans/{p['id']}", TOK)
            print(f"  删除旧计划 id={p['id']} (group {p['group_id']})")

    # 3. 建计划 + 写结果
    def push_plan(gid, form_code, form_title, data, operator, reviewer):
        st, p = req("POST", "/comparison/plans", TOK, {
            "group_id": gid, "year": 2026, "half": 1, "form_code": form_code,
            "form_title": form_title, "compared_at": DATE, "operator": operator, "reviewer": reviewer,
            "conclusion": "可接受", "handle_plan": "无", "status": "done"})
        pid = p["id"]
        quant = []
        for (name, lv), d in data.items():
            if d["ref"] is None: continue
            quant.append({"item": name, "level": lv, "reference_value": str(d["ref"]), "values": {k: str(v) for k,v in d["values"].items() if v is not None}})
        req("PUT", f"/comparison/plans/{pid}/results", TOK, {"quant": quant, "qual": []})
        print(f"  计划 group{gid} id={pid}: {len(quant)} 行")
        return pid

    push_plan(1, "BG-SM-CZ-025", "定量室内比对结果记录分析表（生化分析仪）", sheng, "吕文娟", "金子正")
    push_plan(2, "BG-SM-CZ-024", "定量室内比对结果记录分析表（DXI800分析仪）", dxi, "吕文娟", "金子正")
    push_plan(4, "BG-SM-CZ-027", "定量室内比对结果记录分析表（早孕系列）", zao, "吕文娟", "金子正")
    print("\n>>> 完成。日期统一为", DATE)
