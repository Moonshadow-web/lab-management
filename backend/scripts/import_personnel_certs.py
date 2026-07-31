r"""批量导入人员证书/材料附件到 education-attachments（kind='certificate'）。

源文件夹：C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案
规则：每个子文件夹中，除 .doc/.docx 档案及 Word 临时文件（~$开头）外，
      其余文件均作为该人员的 certificate 附件上传。

默认 dry-run，确认后加 --commit 正式上传。
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DRY_RUN = "--commit" not in sys.argv
HOST = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
USERNAME = "jinzizheng"
PASSWORD = "Jzz6827556"
ROOT = Path(r"C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案")
KIND = "certificate"


def api_call(method, path, data=None, token=None, headers=None):
    url = f"{HOST}{path}"
    h = headers or {}
    h.setdefault("Accept", "application/json")
    if token:
        h["Authorization"] = f"Bearer {token}"
    body = data
    if isinstance(data, dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"status": resp.status, "body": resp.read().decode("utf-8")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", errors="ignore")}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "body": str(e)}


def login() -> str:
    url = f"{HOST}/api/v1/auth/login"
    data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def get_personnel_map(token: str) -> dict[str, int]:
    res = api_call("GET", "/api/v1/education/personnel?page_size=1000", token=token)
    if res["status"] != 200:
        raise RuntimeError(f"无法获取人员主表: {res['status']} {res['body']}")
    body = json.loads(res["body"])
    items = body.get("items", []) if isinstance(body, dict) else body
    return {it.get("name", "").strip(): it.get("id") for it in items if it.get("name")}


def get_existing_certs(person_id: int, token: str) -> dict[str, dict]:
    res = api_call("GET", f"/api/v1/education-attachments/personnel/{person_id}?kind={KIND}", token=token)
    if res["status"] != 200:
        return {}
    body = json.loads(res["body"])
    items = body.get("items", []) if isinstance(body, dict) else body
    return {it.get("original_name", "").strip(): it for it in items}


def build_multipart_body(file_path: Path) -> tuple[bytes, str]:
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()
    fname = file_path.name
    mime = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    fname_escaped = urllib.parse.quote(fname, safe="")
    parts = []
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="files"; filename="{fname}"; '
        f"filename*=UTF-8''{fname_escaped}\r\n".encode("utf-8")
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    with open(file_path, "rb") as f:
        parts.append(f.read())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_cert(person_id: int, file_path: Path, token: str) -> dict:
    body, ct = build_multipart_body(file_path)
    path = f"/api/v1/education-attachments/personnel/{person_id}?kind={KIND}"
    return api_call("POST", path, data=body, token=token, headers={"Content-Type": ct})


def is_archive(f: Path) -> bool:
    return f.suffix.lower() in (".doc", ".docx")


def main():
    print("登录...")
    token = login()
    print("拉取人员主表...")
    pmap = get_personnel_map(token)
    print(f"线上共 {len(pmap)} 人")

    tasks: list[tuple[str, int, list[Path]]] = []
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name.strip()
        pid = pmap.get(name)
        if not pid:
            print(f"[!] 未找到人员：{name}，跳过")
            continue
        files = [
            f for f in folder.iterdir()
            if f.is_file() and not f.name.startswith("~$") and not is_archive(f)
        ]
        if not files:
            print(f"[!] {name} 无证书材料文件")
            continue
        tasks.append((name, pid, files))

    total = sum(len(fs) for _, _, fs in tasks)
    if DRY_RUN:
        print("\n===== DRY RUN（仅扫描，不上传）=====")
        for name, pid, files in tasks:
            print(f"\n{name} (id={pid}):")
            for f in files:
                print(f"  -> {f.name} ({f.stat().st_size / 1024:.1f} KB)")
        print(f"\n共 {total} 个文件待导入。")
        print("确认后运行：python scripts/import_personnel_certs.py --commit")
        return

    print(f"\n开始上传 {total} 个证书材料...")
    ok = skip = fail = 0
    for name, pid, files in tasks:
        existing = get_existing_certs(pid, token)
        print(f"\n{name} (id={pid}):")
        for f in files:
            if f.name in existing:
                print(f"  [SKIP] {f.name} 已存在")
                skip += 1
                continue
            res = upload_cert(pid, f, token)
            if res["status"] == 201:
                print(f"  [OK] {f.name}")
                ok += 1
            else:
                print(f"  [FAIL {res['status']}] {f.name}: {res['body'][:160]}")
                fail += 1
    print(f"\n===== 完成：成功 {ok} / 跳过 {skip} / 失败 {fail} =====")


if __name__ == "__main__":
    main()
