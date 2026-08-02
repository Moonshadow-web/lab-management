import json, urllib.request, urllib.parse, openpyxl, re

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"

_tok = {"v": None}

def login():
    _, l = req_raw("POST", "/auth/login", {"username": "jinzizheng", "password": "Jzz6827556"})
    _tok["v"] = l["access_token"]
    return _tok["v"]

def req_raw(method, path, data=None, token=""):
    url = BASE + path
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        if method == "POST" and path == "/auth/login":
            body = urllib.parse.urlencode(data).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode()
            h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def req(method, path, data=None, token=None):
    """自动在 401 时重登重试一次，规避 CloudRun 多实例瞬时鉴权失败。"""
    if token is None:
        token = _tok["v"] or login()
    st, r = req_raw(method, path, data, token)
    if st == 401:
        token = login()
        st, r = req_raw(method, path, data, token)
    return st, r

_, login = req("POST", "/auth/login", {"username": "jinzizheng", "password": "Jzz6827556"})
tok = login["access_token"]

def paged(path, size=200):
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        st, r = req("GET", f"{path}{sep}page={page}&page_size={size}", tok)
        if st != 200:
            raise RuntimeError(f"{path} {st} {r}")
        items = r.get("items", [])
        out += items
        if len(items) < size or "items" not in r:
            break
        page += 1
    return out

# current scope items
all_items = paged("/accredited-scope?page_size=2000")
ac = [i for i in all_items if i["category_l2"] == "AC 临床化学"]
print(f"AC 临床化学共 {len(ac)} 项")

# reagents
allr = paged("/reagent/items?show_inactive=true", 200)
rname = {x["id"]: x["name"] for x in allr}
# instruments
inst = paged("/instruments?page_size=1000", 1000)
iname = {i["id"]: i["name"] for i in inst}
# test_items
ti = paged("/test-items", 500)

# AST reagent id
ast_id = None
for x in allr:
    if "天门冬氨酸" in x["name"] or "OSR6109" in str(x["name"]):
        ast_id = x["id"]
        print("AST reagent found:", ast_id, x["name"])

# CRP original text from xlsx
xlsx = openpyxl.load_workbook(r"D:/民航总医院/15189/生免认可申请附表/生免组申请认可的能力范围.xlsx", data_only=True).active
crp_orig = None
for r in range(1, xlsx.max_row + 1):
    b = xlsx.cell(r, 2).value
    if b and "反应蛋白" in str(b):
        crp_orig = xlsx.cell(r, 6).value
print("CRP original reagent:", crp_orig)

def strip_osr(name):
    if not name:
        return name
    return re.sub(r"^OSR\d+[-/]\s*", "", name).strip()

SAMPLE_WORDS = ["尿液", "脑脊液", "胸腹水", "腹水", "粪便", "唾液", "羊水", "血清",
                "血浆", "全血", "分泌物", "胃液", "胆汁", "滑膜液", "精液",
                "支气管肺泡灌洗液", "房水", "泪液", "乳汁", "精液"]

def norm(s):
    s = re.sub(r"[（(].*?[)）]", "", s)
    for w in SAMPLE_WORDS:
        s = s.replace(w, "")
    s = s.replace("门", "").replace(" ", "").replace("－", "-").replace("—", "-")
    return s

def find_method(ac_name):
    """精确匹配 analyte 核心（去除样本类型/括号修饰），避免子串误配。"""
    ac_n = norm(ac_name)
    exact = []
    for t in ti:
        tn = t.get("name", "")
        if norm(tn) == ac_n:
            penalty = 1 if any(w in tn for w in SAMPLE_WORDS) else 0
            exact.append((penalty, t.get("method"), tn))
    if exact:
        exact.sort(key=lambda x: x[0])
        return exact[0][1], exact[0][2]
    return None, None

print("\n%-4s %-14s | %-22s -> %-22s | method: %-16s -> %-16s" % ("id","项目","旧试剂","新试剂","旧方法","新方法"))
updates = []
for i in ac:
    iid = i["id"]
    old_reag = i["reagent_name"] or ""
    old_meth = i["method_name"] or ""
    payload = {}
    note = []

    # ---- reagent ----
    if iid == 18:  # AST
        if ast_id:
            payload["reagent_id"] = ast_id
            payload["reagent_name"] = strip_osr(rname[ast_id])
            note.append("AST→OSR6109")
        else:
            note.append("AST未找到系统试剂")
    elif iid == 34:  # CRP 保留原
        payload["reagent_id"] = None
        payload["reagent_name"] = crp_orig or old_reag
        note.append("CRP还原原文本")
    elif iid == 33:  # 糖化 东曹，试剂不关联
        note.append("糖化:试剂不关联(系统sebia错)")
    elif i.get("reagent_id"):  # 其它已关联OSR -> 去前缀
        payload["reagent_id"] = i["reagent_id"]
        payload["reagent_name"] = strip_osr(old_reag)
        note.append("去OSR前缀")

    # ---- method from test_items ----
    if iid == 34:  # C反应蛋白：用户要求保留原（试剂+方法）
        note.append("CRP保留原方法")
    elif iid == 23:  # 碱性磷酸酶：系统写"NNP"疑似笔误，保留 Excel 正确值 NPP
        note.append("ALP保留原方法(系统NNP疑似笔误待修)")
    else:
        meth, src = find_method(i["item_name"])
        if meth:
            payload["method_name"] = meth
            note.append(f"方法←{src}")
        else:
            note.append("方法未匹配(保留原)")

    # build display
    new_reag = payload.get("reagent_name", old_reag)
    new_meth = payload.get("method_name", old_meth)
    print("%-4d %-14s | %-22s -> %-22s | %-16s -> %-16s | %s" % (
        iid, i["item_name"][:14], old_reag[:20], new_reag[:20], old_meth[:14], str(new_meth)[:14], ";".join(note)))

    if payload:
        updates.append((iid, payload))

APPLY = __import__("os").environ.get("APPLY") == "1"
print(f"\n{'== APPLY 模式 ==' if APPLY else '== DRY-RUN 模式(未落库) =='} 共 {len(updates)} 项")
ok = 0
for iid, payload in updates:
    if not APPLY:
        print(f"  [dry] PUT /accredited-scope/{iid} -> {payload}")
        continue
    st, r = req("PUT", f"/accredited-scope/{iid}", payload, tok)
    if st == 200:
        ok += 1
    else:
        print("  FAIL", iid, st, r)
if APPLY:
    print(f"更新成功 {ok}/{len(updates)}")
