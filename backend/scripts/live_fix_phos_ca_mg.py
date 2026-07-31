"""线上修复：尿液 docx 单位+质量目标（_12.docx）补充步骤。

前提：已部署 a42d5d7（BUILD_MARK=qc-urine-phos-ca-fix-2026-07-26），新种子含
血清 磷/总钙 精确保护行，阻断尿液（尿液）同名项污染血清目标。

本脚本按顺序：
1. 登录 admin（jinzizheng）
2. POST /quality-requirements/_meta/seed  —— 幂等，新增 磷/总钙 精确行
3. PUT /quality-requirements/{id} 镁 cv 5.5%→8.3%（种子幂等不会覆盖已存在行，须手动 PUT）
4. POST /qc-summaries/_backfill_goals   —— 全量重算，血清磷 7.7%→4.0%、总钙 10.3%→2.0%、镁→8.3%
5. POST /qc-summaries/_backfill_units   —— 单位再对齐（幂等）
"""
import urllib.request, urllib.parse, json

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
USER, PWD = "jinzizheng", "Jzz6827556"


def _req(method, path, token=None, data=None, form=False):
    url = BASE + path
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if form:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = b""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    st, body = _req("POST", "/auth/login", form=True, data={"username": USER, "password": PWD})
    if st != 200 or "access_token" not in body:
        print("LOGIN FAIL", st, body)
        return
    token = body["access_token"]
    print("login OK, roles=", body.get("roles"))

    # 2. seed
    st, body = _req("POST", "/quality-requirements/_meta/seed", token=token)
    print("seed:", st, body)

    # 3. find 镁 wst403-2024
    st, body = _req("GET", "/quality-requirements?source=wst403-2024&q=%E9%95%81&page_size=500", token=token)
    print("mg list:", st, "total=", body.get("total") if isinstance(body, dict) else body)
    mg_id = None
    if isinstance(body, dict):
        for it in body.get("items", []):
            if it.get("item_name") == "镁" and it.get("source") == "wst403-2024":
                mg_id = it["id"]
                print("  found 镁 id=", mg_id, "cv=", it.get("cv"))
                break
    if mg_id is None:
        print("  !! 未找到 wst403-2024 的 镁 行，跳过 PUT")
    else:
        st, body = _req("PUT", f"/quality-requirements/{mg_id}", token=token, data={"cv": "8.3%"})
        print("mg PUT:", st, body)

    # 4. backfill goals
    st, body = _req("POST", "/qc-summaries/_backfill_goals", token=token)
    if isinstance(body, dict):
        print("backfill_goals:", st, "updated=", body.get("updated"), "/", body.get("total"))
        # 打印与本次修复相关的样本
        rel = [s for s in body.get("samples", []) if s.get("test_item") in ("磷", "总钙", "镁", "磷（尿液）", "总钙（尿液）", "尿磷", "尿钙", "尿镁")]
        if rel:
            print("  samples(相关):", json.dumps(rel, ensure_ascii=False))
    else:
        print("backfill_goals:", st, body)

    # 5. backfill units
    st, body = _req("POST", "/qc-summaries/_backfill_units", token=token)
    print("backfill_units:", st, body)


if __name__ == "__main__":
    main()
