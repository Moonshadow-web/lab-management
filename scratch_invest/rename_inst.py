#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归整 AU/DXI800 仪器 name 为科室代号式，并备份原值便于回滚。"""
import json, urllib.request, urllib.parse, datetime
HOST = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
TOKEN = None

# id -> 新 name（代号式；型号 model 原值保留）
RENAME = {
    # 在用 AU 生化仪
    5:  "AU5800",
    67: "AU58-1",
    68: "AU58-2",
    # 在用 DXI800 化学发光
    69: "DXI800 1号机",
    70: "DXI800 2号机",
    71: "DXI800 3号机",
    72: "DXI800 4号机",
    73: "DXI800 急诊",
    74: "DXI800 唐筛",
    # 停用旧机（加「停用」后缀，便于区分）
    2:  "AU5822（停用）",
    3:  "DXI800 C（停用）",
    4:  "DXI800 D（停用）",
    6:  "DXI800 急诊（停用）",
    7:  "DXI800 唐筛（停用）",
}


def login():
    global TOKEN
    body = urllib.parse.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(HOST + "/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        TOKEN = json.loads(r.read().decode()).get("access_token", "")


def get(path):
    req = urllib.request.Request(HOST + path, headers={"Authorization": "Bearer " + TOKEN}, method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def put(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(HOST + path, data=body,
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}, method="PUT")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    login()
    # 1) 备份全部仪器
    all_inst = []
    page = 1
    while True:
        r = get(f"/api/v1/instruments?page={page}&page_size=100")
        all_inst.extend(r.get("items", []))
        if len(all_inst) >= r.get("total", 0) or not r.get("items"):
            break
        page += 1
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"scratch_invest/instruments_backup_{ts}.json"
    with open(bak, "w", encoding="utf-8") as f:
        json.dump(all_inst, f, ensure_ascii=False, indent=2)
    print(f"备份 {len(all_inst)} 台仪器 -> {bak}")

    # 2) 重命名
    ok = 0
    for iid, new_name in RENAME.items():
        before = next((x["name"] for x in all_inst if x["id"] == iid), None)
        try:
            put(f"/api/v1/instruments/{iid}", {"name": new_name})
            print(f"  id={iid:<3} {before!r:<18} -> {new_name!r}  OK")
            ok += 1
        except Exception as e:
            print(f"  id={iid:<3} {before!r:<18} -> {new_name!r}  FAIL {e}")
    print(f"renamed {ok}/{len(RENAME)}")

    # 3) 复核：拉回这 14 台确认
    after = {x["id"]: x["name"] for x in get("/api/v1/instruments?page=1&page_size=100").get("items", [])}
    print("--- 复核 ---")
    for iid, new_name in RENAME.items():
        print(f"  id={iid:<3} now={after.get(iid)!r:<18} expect={new_name!r}")


if __name__ == "__main__":
    main()
