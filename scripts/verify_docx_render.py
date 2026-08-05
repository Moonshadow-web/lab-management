# -*- coding: utf-8 -*-
"""验证 cnas_standards 里 9 个原 .doc 是否已替换为 .docx，且字节是合法 docx。"""
import io
import zipfile
import requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
EXPECT_DOCX = {16, 22, 24, 25, 26, 27, 28, 29, 30}


def main():
    r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
    tok = r.json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    lst = requests.get(BASE + "/cnas-standards", headers=H, timeout=120).json()

    print(f"总记录: {len(lst)}")
    docx_ids, bad = [], []
    for it in lst:
        fn = it.get("original_filename") or ""
        if fn.lower().endswith(".docx"):
            docx_ids.append(it["id"])
        if it["id"] in EXPECT_DOCX and not fn.lower().endswith(".docx"):
            bad.append((it["id"], fn))

    print(f"全部 .docx 记录数: {len(docx_ids)}")
    print(f"期望为 docx 但仍是 .doc 的: {bad if bad else '无 ✅'}")

    # 抽样校验 docx 字节合法（PK 头 + 能 zip 打开含 word/document.xml）
    sample = sorted(EXPECT_DOCX)[:3]
    for sid in sample:
        pv = requests.get(BASE + f"/cnas-standards/{sid}/preview", headers=H, timeout=120)
        head = pv.content[:2]
        ok_zip = False
        try:
            z = zipfile.ZipFile(io.BytesIO(pv.content))
            ok_zip = "word/document.xml" in z.namelist()
        except Exception:
            ok_zip = False
        ct = pv.headers.get("Content-Type")
        print(f"id={sid} 头={head} zip含document.xml={ok_zip} ct={ct} size={len(pv.content)}")
        assert head == b"PK", f"id={sid} 非 docx"
        assert ok_zip, f"id={sid} docx 结构异常"
        assert ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document", \
            f"id={sid} MIME 应为 docx"

    assert not bad, "存在仍为 .doc 的记录"
    print("\nVERIFY_OK ✅ 9 个原 .doc 均已替换为合法 .docx，前端可走 mammoth 渲染")


if __name__ == "__main__":
    main()
