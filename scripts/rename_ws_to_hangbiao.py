"""把系统内 cnas_standards 中 category='卫生行业标准(WS/T)' 的记录统一改名为 '行标'，
使分类与用户期望的三类（CNAS认可规范 / CNAS附件表 / 行标）一致。

默认 DRY_RUN；APPLY=1 执行。
"""
import os
import sys

import requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
OLD = "卫生行业标准(WS/T)"
NEW = "行标"

APPLY = os.environ.get("APPLY") == "1"


def main():
    r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    lst = requests.get(BASE + "/cnas-standards", headers=H, timeout=120).json()
    targets = [it for it in lst if it.get("category") == OLD]
    print(f"匹配到 {len(targets)} 条 category={OLD!r} 的记录:")
    for t in targets:
        print(f"  id={t['id']} code={t['code']!r} name={t['name'][:28]!r}")

    if not targets:
        return
    if not APPLY:
        print("\n[DRY_RUN] 未执行改名。APPLY=1 以执行。")
        return

    ok, fail = [], []
    for t in targets:
        rr = requests.patch(BASE + f"/cnas-standards/{t['id']}",
                            json={"category": NEW}, headers=H, timeout=120)
        if rr.status_code >= 300:
            fail.append((t["id"], rr.status_code, rr.text[:120]))
        else:
            ok.append(t["id"])
    print(f"\n改名完成: 成功={len(ok)} 失败={len(fail)}")
    if fail:
        for i, st, msg in fail:
            print(f"  id={i} [{st}] {msg}")


if __name__ == "__main__":
    main()
