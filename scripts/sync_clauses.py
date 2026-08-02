"""把 clauses_export.json 同步到线上 audit_clauses 表。
按 clause_no 匹配更新；不存在的创建；clause_no 格式异常的老数据删除。
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
USERNAME = "jinzizheng"
PASSWORD = "Jzz6827556"


def api_request(method: str, path: str, data: dict | None = None, token: str = "") -> dict | list:
    url = BASE + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        if method == "POST" and path == "/auth/login":
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"{method} {path} {e.code}: {text[:300]}")


def login() -> str:
    r = api_request("POST", "/auth/login", {"username": USERNAME, "password": PASSWORD})
    return r["access_token"]


def main():
    token = login()
    export_path = Path(__file__).resolve().parent.parent / "clauses_export.json"
    with open(export_path, encoding="utf-8") as f:
        parsed = json.load(f)

    # 获取现有条款
    existing_resp = api_request("GET", "/audit-clauses?page_size=2000", token=token)
    existing_items = existing_resp.get("items") or existing_resp or []
    by_no: dict[str, dict] = {}
    malformed_ids = []
    valid_re = re.compile(r"^\d+(?:\.\d+)+$")
    for it in existing_items:
        no = (it.get("clause_no") or "").strip()
        if not no:
            continue
        if no in by_no:
            # 重复的旧数据，留后删除
            malformed_ids.append(it["id"])
        elif valid_re.match(no):
            by_no[no] = it
        else:
            malformed_ids.append(it["id"])

    created = updated = unchanged = 0
    for c in parsed:
        no = c["clause_no"]
        payload = {
            "clause_no": no,
            "chapter": c.get("chapter", ""),
            "title": c.get("title", ""),
            "content": c.get("content", ""),
            "check_point": c.get("check_point", ""),
            "application_requirement": c.get("application_requirement", ""),
        }
        if no in by_no:
            old = by_no[no]
            if (
                old.get("chapter") == payload["chapter"]
                and old.get("title") == payload["title"]
                and old.get("content") == payload["content"]
                and old.get("check_point") == payload["check_point"]
                and old.get("application_requirement") == payload["application_requirement"]
            ):
                unchanged += 1
            else:
                api_request("PUT", f"/audit-clauses/{old['id']}", payload, token=token)
                updated += 1
        else:
            api_request("POST", "/audit-clauses", payload, token=token)
            created += 1

    deleted = 0
    for rid in malformed_ids:
        try:
            api_request("DELETE", f"/audit-clauses/{rid}", token=token)
            deleted += 1
        except Exception as e:
            print(f"  删除 {rid} 失败: {e}")

    print(f"同步完成：创建 {created}，更新 {updated}，无变化 {unchanged}，删除异常 {deleted}")


if __name__ == "__main__":
    main()
