"""线上修复：血气分析仪单位+质量目标（_13.docx）。

前提：origin/main 已含 commit 4938f3d（BLOODGAS_DOCX_ITEMS + tHb 单位 g/L）。
即使线上服役容器_BUILD_MARK 被别的 AI 覆盖，只要代码树含本改动，seed/backfill 即生效。
本脚本：
1. seed  —— 新增 13 条血气精确行（Ca++/K+/Na+/PCO2/pH/PO2/tHb/乳酸/氧和/碳氧/氯./血糖/高铁血红蛋白）
2. backfill_goals —— 全量重算，血气项按新目标（pH=2%、PCO2 2.7%、PO2 4.2%、Na+ 1.3%、Ca++ 1.7%、tHb 2.0%、高铁血红蛋白 5.0%...）
3. backfill_units  —— tHb 单位 mmol/L(空)→g/L
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
    req = urllib.request.Request(BASE + "/auth/login",
        data=urllib.parse.urlencode({"username": USER, "password": PWD}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    token = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())["access_token"]

    st, body = _req("POST", "/quality-requirements/_meta/seed", token=token)
    print("seed:", st, "added=", body.get("added"), "updated=", body.get("updated"), "skipped=", body.get("skipped"))

    st, body = _req("POST", "/qc-summaries/_backfill_goals", token=token)
    print("backfill_goals:", st, "updated=", body.get("updated"), "/", body.get("total"))
    rel = [s for s in body.get("samples", []) if s.get("test_item") in (
        "Ca++", "K+", "Na+", "PCO2", "pH", "PO2", "tHb", "乳酸",
        "氧和血红蛋白比率", "碳氧血红蛋白比率", "氯.", "血糖", "高铁血红蛋白")]
    if rel:
        print("  samples(血气):", json.dumps(rel, ensure_ascii=False))

    st, body = _req("POST", "/qc-summaries/_backfill_units", token=token)
    print("backfill_units:", st, "updated=", body.get("updated"))
    rel_u = [s for s in body.get("samples", []) if s.get("test_item") in ("tHb",)]
    if rel_u:
        print("  samples(单位):", json.dumps(rel_u, ensure_ascii=False))


if __name__ == "__main__":
    main()
