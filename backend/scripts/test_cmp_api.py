"""验证仪器间比对后端改动：登录、500->400、仪器选项(型号)、按档案解析共有项目。"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8123/api/v1"


def _req(method, path, token=None, data=None, form=None):
    url = f"{BASE}{path}"
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    st, d = _req("POST", "/auth/login",
                 form={"username": "jinzizheng", "password": "Jzz6827556"})
    assert st == 200, (st, d)
    tok = d["access_token"]
    print("== login OK ==")

    # 1) 仪器选项（型号显示）
    st, d = _req("GET", "/comparison/instruments/options", token=tok)
    print("instruments/options:", st, "count=", len(d))
    for x in d[:8]:
        print("   ", x["id"], "| name=", x["name"], "| model=", x["model"], "| status=", x["status"])

    # 2) 现有分组
    st, groups = _req("GET", "/comparison/groups", token=tok)
    print("groups:", st, "count=", len(groups))
    for g in groups:
        print("   ", g["id"], g["name"], "ids=", g["instrument_ids"],
              "ref=", g["reference_instrument_id"], "items=", len(g["items"]))

    # 3) 重复名称 -> 应 400（非 500）
    if groups:
        dup = groups[0]["name"]
        st, d = _req("POST", "/comparison/groups", token=tok,
                     data={"name": dup, "category": "定量"})
        print("dup-name create:", st, d)

    # 4) 按档案解析共有项目
    bio = next((g for g in groups if "生化" in g["name"]), groups[0] if groups else None)
    if bio:
        ids = bio["instrument_ids"]
        st, d = _req("POST", "/comparison/groups/resolve-items", token=tok,
                     data={"instrument_ids": ids, "category": "定量", "min_count": 2})
        print("resolve-items:", st, "instruments=", d.get("instruments"),
              "item_count=", len(d.get("items", [])))
        for it in d.get("items", [])[:12]:
            print("   ", it["name"], "|", it["label"], "| te=", it["te"],
                  "| appl_ids=", it["instrument_ids"])


if __name__ == "__main__":
    main()
