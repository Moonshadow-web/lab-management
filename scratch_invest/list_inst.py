#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse
HOST = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
TOKEN = None


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


login()
r = get("/api/v1/instruments?page=1&page_size=100")
print("total instruments:", r.get("total"))
for i in r.get("items", []):
    print(f"id={i['id']:>3} | name={i['name']!r:<28} | model={i.get('model')!r:<16} | dept_no={i.get('dept_no')!r:<8} | category={i.get('category')!r:<10} | status={i.get('status')}")
