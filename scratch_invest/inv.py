#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse

HOST = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
TOKEN = None


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


login()
print("=== test items containing 免疫球蛋白 ===")
ti = get("/api/v1/test-items?q=" + urllib.parse.quote("免疫球蛋白") + "&page_size=50")
for t in ti.get("items", []):
    print(t["id"], repr(t["name"]), "aliases=", t.get("aliases", ""))

print("\n=== reagents containing 单纯疱疹 ===")
ri = get("/api/v1/reagent/items?q=" + urllib.parse.quote("单纯疱疹") + "&page_size=50")
for r in ri.get("items", []):
    print(r["id"], repr(r["name"]), "type=", r["type"])

print("\n=== test_item_reagents rows mentioning 免疫球蛋白 or 单纯疱疹 ===")
for kw in ["免疫球蛋白", "单纯疱疹"]:
    tr = get("/api/v1/reagent/associations/test-items?q=" + urllib.parse.quote(kw) + "&page_size=50")
    print(f"-- q={kw}: total={tr['total']}")
    for row in tr.get("items", []):
        print("   rel_id", row["id"], "| test:", row["test_item_name"], "| reagent:", row["reagent_name"],
              "| role:", row["role"], "| auto:", row["auto_matched"])
