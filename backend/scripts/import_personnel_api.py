"""通过线上 API 把生免室人员档案导入 personnel_master。

用法：
    cd backend
    python scripts/import_personnel_api.py

需确保教育模块已部署（personnel_master 表已创建）。
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

HOST = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
USERNAME = "jinzizheng"
PASSWORD = "Jzz6827556"
ROOT = Path(r"C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案")

LABEL_MAP = {
    "姓名": "name",
    "性别": "gender",
    "出生年月": "birth_date",
    "学历": "education",
    "职称": "title",
    "职务": "position",
    "政治面貌": "political_status",
    "组内职责": "group_duty",
    "参加工作": "work_start",
    "来院时间": "hospital_join",
    "来组时间": "group_join",
}


def antiword(path: Path) -> str:
    return subprocess.run(
        ["antiword", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", check=False
    ).stdout


def extract_basic(text: str) -> dict[str, str]:
    import re
    m = re.search(r"一、基本情况\s*(.+?)二、", text, re.S)
    if not m:
        return {}
    section = m.group(1)
    result: dict[str, str] = {}
    for line in section.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        for i in range(1, len(cells) - 1, 2):
            label = re.sub(r"\s+", "", cells[i])
            value = cells[i + 1].strip()
            if not label or not value:
                continue
            key = LABEL_MAP.get(label)
            if key:
                result[key] = value
    return result


def find_doc_file(folder: Path) -> Path | None:
    docs = list(folder.glob("*.doc"))
    return docs[0] if docs else None


def api_call(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{HOST}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", errors="ignore")}


def login() -> str:
    import urllib.parse
    url = f"{HOST}/api/v1/auth/login"
    data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    return res["access_token"]


def main():
    print("登录...")
    token = login()
    print("登录成功，开始导入...")

    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():
            continue
        doc = find_doc_file(folder)
        if not doc:
            print(f"[!] {folder.name}: 未找到 .doc 档案")
            continue
        data = extract_basic(antiword(doc))
        if not data.get("name"):
            data["name"] = folder.name
        payload = {
            "name": data.get("name", ""),
            "gender": data.get("gender", ""),
            "birth_date": data.get("birth_date", ""),
            "education": data.get("education", ""),
            "title": data.get("title", ""),
            "position": data.get("position", ""),
            "political_status": data.get("political_status", ""),
            "group_duty": data.get("group_duty", ""),
            "work_start": data.get("work_start", ""),
            "hospital_join": data.get("hospital_join", ""),
            "group_join": data.get("group_join", ""),
        }
        res = api_call("POST", "/api/v1/education/personnel", payload, token)
        if res["status"] == 201:
            print(f"[OK] {payload['name']} -> id={res['body'].get('id')}")
        else:
            print(f"[FAIL] {payload['name']}: {res['status']} {res['body']}")


if __name__ == "__main__":
    main()
