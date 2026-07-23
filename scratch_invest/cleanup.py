#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描并清理 projects<->reagents 中靠裸「抗体类别代号」(igg/igm/iga/ige)
误命中的自动关联。校验规则：仅当项目全名或「非通用」别名是试剂名的子串
（或反之）时才视为有效；否则判定为误匹配并删除。"""
import json, re, os, urllib.request, urllib.parse

HOST = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
TOKEN = None
GENERIC = {"igg", "igm", "iga", "ige", "ig"}
DRY = os.environ.get("DRY") == "1"


def norm(s):
    s = str(s or "")
    s = re.sub(r"[Rr][1-9]\b", "", s)
    s = re.sub(r"[^0-9A-Za-z一-鿿]", "", s)
    return s.strip().lower()


def login():
    global TOKEN
    body = urllib.parse.urlencode({"username": "jinzizheng",
                                    "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(HOST + "/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        TOKEN = json.loads(r.read().decode()).get("access_token", "")


def get(path):
    req = urllib.request.Request(HOST + path, headers={"Authorization": "Bearer " + TOKEN}, method="GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def delete(rel_id):
    req = urllib.request.Request(HOST + f"/api/v1/reagent/associations/test-items/{rel_id}",
                                 headers={"Authorization": "Bearer " + TOKEN}, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main():
    login()
    # 1) 测试项目 id -> (name, aliases)
    ti = get("/api/v1/test-items?page_size=300")
    timap = {}
    for t in ti.get("items", []):
        timap[t["id"]] = (t["name"], t.get("aliases", "") or "")

    # 2) 翻页读取全部 自动 项目<->试剂 关联
    rows, page = [], 1
    while True:
        tr = get(f"/api/v1/reagent/associations/test-items?auto_only=true&page={page}&page_size=200")
        rows.extend(tr.get("items", []))
        total = tr.get("total", 0)
        if len(rows) >= total or not tr.get("items"):
            break
        page += 1
    print(f"total auto test_item_reagents rows = {len(rows)}")

    flagged = []
    for row in rows:
        if not row.get("auto_matched"):
            continue
        tid = row["test_item_id"]
        name, aliases = timap.get(tid, ("", ""))
        rn = norm(row["reagent_name"])
        cands = [norm(name)] + [norm(a) for a in aliases.split(",") if a.strip()]
        cands = [c for c in cands if c and c not in GENERIC]
        ok = any((c in rn) or (rn in c) for c in cands)
        if not ok:
            flagged.append((row["id"], name, row["reagent_name"]))

    print(f"flagged false-positive auto associations = {len(flagged)}")
    for rid, tn, rn in flagged:
        print("  DELETE rel_id", rid, "| test:", tn, "| reagent:", rn)

    # 3) 删除
    deleted = 0
    for rid, tn, rn in flagged:
        if DRY:
            print("  [DRY] would delete", rid)
            deleted += 1
            continue
        try:
            st = delete(rid)
            if st in (200, 204):
                deleted += 1
                print("  -> deleted", rid)
        except Exception as e:
            print("  -> FAILED", rid, e)
    print(f"deleted {deleted}/{len(flagged)}")


if __name__ == "__main__":
    main()
