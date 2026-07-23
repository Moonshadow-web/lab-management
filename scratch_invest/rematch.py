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


def post(path):
    req = urllib.request.Request(HOST + path, headers={"Authorization": "Bearer " + TOKEN}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


login()
print(post("/api/v1/reagent/associations/_auto-match?reset=false"))
