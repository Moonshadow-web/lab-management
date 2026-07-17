import json, urllib.request, urllib.parse

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
USER, PWD = "jinzizheng", "Jzz6827556"


def req(method, path, data=None, token=None):
    url = BASE + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


# 1) 登录（form 表单）
login_req = urllib.request.Request(
    BASE + "/api/v1/auth/login",
    data=urllib.parse.urlencode({"username": USER, "password": PWD}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
with urllib.request.urlopen(login_req, timeout=30) as resp:
    tok = json.loads(resp.read().decode())["access_token"]
print("login OK" if tok else "login FAIL")
assert tok

# 2) 列出所有批号，找 华兴康 + lot 22060430
s, lst = req("GET", "/api/v1/qc-target-batches?page=1&page_size=500", token=tok)
print("list status", s, "total", lst.get("total"))
items = lst.get("items", lst.get("data", []))
matches = [b for b in items
           if ("华兴康" in (b.get("qc_material") or "")) and b.get("lot_no") == "22060430"]
print("匹配批号数:", len(matches))
for m in matches:
    print("  -> id", m["id"], m.get("qc_material"), "lot", m.get("lot_no"))

# 3) 逐个改 lot_no -> 20260430
for m in matches:
    bid = m["id"]
    payload = {k: m.get(k) for k in ("qc_material", "lot_no", "level", "instrument", "method", "mode", "note")}
    payload["lot_no"] = "20260430"
    s2, up = req("PUT", f"/api/v1/qc-target-batches/{bid}", data=payload, token=tok)
    print(f"  PUT {bid}: status={s2} new_lot={up.get('lot_no')}")

print("DONE")
