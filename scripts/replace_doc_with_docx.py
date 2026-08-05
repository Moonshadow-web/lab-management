# -*- coding: utf-8 -*-
"""把本地转换好的 .docx 替换进系统 cnas_standards 里对应的 .doc 记录。

匹配规则：系统记录 original_filename 去掉 .doc 后缀得到 stem，与本地 .docx 文件名
（去掉 .docx 后缀）精确比对。命中即调用 POST /{id}/replace 上传新二进制。

replace 端点会同步更新 original_filename / file_size / cloud_key，因此记录扩展名
也会从 .doc 变为 .docx，前端即可按 docx 走 mammoth 渲染预览。

默认 DRY_RUN；APPLY=1 才真正上传。
"""
import os
import sys
import requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
SRC_DIRS = [
    r"D:\民航总医院\15189\15189规范文件",
    r"D:\民航总医院\15189\15189规范文件\CNAS医学实验室认可申请书及附件20231201",
]
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def stem(fn):
    return os.path.splitext(fn)[0].rstrip()


def get_docx_files():
    files = {}
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            print(f"[WARN] 目录不存在，跳过: {d}")
            continue
        for name in os.listdir(d):
            low = name.lower()
            if low.endswith(".docx"):
                files.setdefault(stem(name), os.path.join(d, name))
    return files


def main():
    r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    lst = requests.get(BASE + "/cnas-standards", headers=H, timeout=120).json()

    local = get_docx_files()
    targets = {}
    for it in lst:
        fn = it.get("original_filename") or ""
        low = fn.lower()
        if low.endswith(".doc") and not low.endswith(".docx"):
            targets[stem(fn)] = it

    print(f"本地 docx: {len(local)}  系统 .doc 记录: {len(targets)}")
    apply = os.environ.get("APPLY") == "1"
    if not apply:
        print(">>> DRY_RUN（设置 APPLY=1 才真正替换）\n")

    ok = skip = fail = 0
    for s, rec in sorted(targets.items()):
        if s in local:
            path = local[s]
            size = os.path.getsize(path)
            print(f"[{rec['id']}] {rec['original_filename']}  ->  替换 {os.path.basename(path)} ({size} B)")
            if apply:
                with open(path, "rb") as f:
                    content = f.read()
                resp = requests.post(
                    BASE + f"/cnas-standards/{rec['id']}/replace",
                    headers=H,
                    files={"file": (os.path.basename(path), content, DOCX_MIME)},
                    timeout=120,
                )
                if resp.status_code >= 400:
                    print("      FAIL", resp.status_code, resp.text[:200])
                    fail += 1
                else:
                    j = resp.json()
                    print("      OK  new_fn=", j.get("original_filename"), " size=", j.get("file_size"))
                    ok += 1
        else:
            print(f"[{rec['id']}] {rec['original_filename']}  ->  本地无对应 docx，跳过")
            skip += 1

    print(f"\n汇总: 替换成功={ok}  无本地docx={skip}  失败={fail}")
    return fail


if __name__ == "__main__":
    sys.exit(main())
