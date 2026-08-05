"""把线上 cnas_standards 中 code=CNAS-CL02-2023 的记录(id=1)的 PDF 二进制
替换为用户提供的新文件（DTJY-WLWJ-2.0-01 版 CNAS-CL02:2023）。

保留 code/name/category/sort_order 等元数据，仅替换文件字节。
默认 DRY_RUN；APPLY=1 执行。
"""
import os
import sys

import requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
NEW_FILE = r"C:/Users/81526/xwechat_files/wxid_z4wstvohwlju21_b876/msg/file/2026-08/DTJY-WLWJ-2.0-01 CNAS-CL02：2023《医学实验室质量和能力认可准则》.pdf"
TARGET_CODE = "CNAS-CL02-2023"

APPLY = os.environ.get("APPLY") == "1"


def main():
    r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    lst = requests.get(BASE + "/cnas-standards", headers=H, timeout=120).json()
    target = [it for it in lst if it.get("code") == TARGET_CODE]
    if not target:
        print(f"[ERROR] 未找到 code={TARGET_CODE} 的记录")
        sys.exit(1)
    if len(target) > 1:
        print(f"[ERROR] 匹配到多条 code={TARGET_CODE}: {[t['id'] for t in target]}")
        sys.exit(1)
    rec = target[0]
    print(f"目标记录: id={rec['id']} code={rec['code']!r} name={rec['name']!r} "
          f"原file_size={rec['file_size']} 原original_filename={rec['original_filename']!r}")

    new_size = os.path.getsize(NEW_FILE)
    print(f"新文件: {os.path.basename(NEW_FILE)} size={new_size}")

    if not APPLY:
        print("\n[DRY_RUN] 未执行替换。APPLY=1 以执行。")
        return

    with open(NEW_FILE, "rb") as f:
        files = {"file": (os.path.basename(NEW_FILE), f, "application/pdf")}
        rr = requests.post(BASE + f"/cnas-standards/{rec['id']}/replace",
                           files=files, headers=H, timeout=300)
    if rr.status_code >= 300:
        print(f"[ERROR] 替换失败 status={rr.status_code} body={rr.text[:300]}")
        sys.exit(1)
    out = rr.json()
    print(f"\n[OK] 已替换 id={out['id']} code={out['code']!r}")
    print(f"    新 original_filename={out['original_filename']!r}")
    print(f"    新 file_size={out['file_size']} (期望={new_size})")
    assert out["file_size"] == new_size, "file_size 与本地新文件不一致"


if __name__ == "__main__":
    main()
