#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""针对性抓取北京市肝炎标志物(code=21)成绩回报：直接用快照里的 CDN 直链下载
「汇总」+「统计结果表(定性)」两份 PDF 合并，写入 plan 88（第1次）。
不依赖重新拉列表（会话 cookie 已过期），仅用快照中已解析出的永久 CDN 链接。
"""
import json
import sqlite3
import time
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "app.db"
REPORT_DIR = BASE_DIR / "data" / "eqa_reports"
COOKIE_FILE = BASE_DIR / "outputs" / "bj_cookies.txt"
LINKS_JSON = BASE_DIR / "outputs" / "eqa_bj_links.json"
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
TARGET_PLAN_ID = 88
TARGET_CODE = "21"
OUT_REL = f"eqa_reports/肝炎标志物_第1次_{TARGET_PLAN_ID}.pdf"


def load_cookie():
    jar = requests.cookies.RequestsCookieJar()
    if COOKIE_FILE.exists():
        for pair in COOKIE_FILE.read_text(encoding="utf-8").strip().split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                for dom in (".clinet.com.cn", "pdf.clinet.cn"):
                    jar.set(k.strip(), v.strip(), domain=dom, path="/")
    return jar


def download_pdf(href, jar):
    r = requests.get(href, cookies=jar, timeout=60,
                     headers={"User-Agent": DESKTOP_UA,
                               "Referer": "https://www.clinet.com.cn/clinetbusiness/hospital/desktop/DataAdminArea4.asp"})
    print("  HTTP", r.status_code, "bytes", len(r.content), href.split("/")[-1])
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").lower()
    if "application/pdf" not in ctype and not r.content.startswith(b"%PDF"):
        raise ValueError(f"非 PDF：{ctype}")
    return r.content


def main():
    data = json.load(open(LINKS_JSON, encoding="utf-8"))
    hrefs = {}
    for d in data:
        if d.get("code") == TARGET_CODE:
            hrefs[d["sub"]] = d["href"]
    print("code=%s 解析到链接: %s" % (TARGET_CODE, list(hrefs.keys())))
    summary = hrefs.get("汇总")
    result = hrefs.get("定量") or hrefs.get("定性")
    if not summary and not result:
        raise SystemExit("code=%s 快照中无可用 PDF 链接" % TARGET_CODE)

    jar = load_cookie()
    parts = []
    if summary:
        parts.append(("汇总", download_pdf(summary, jar)))
    if result:
        parts.append(("统计结果表", download_pdf(result, jar)))

    writer = PdfWriter()
    for _, b in parts:
        for pg in PdfReader(BytesIO(b)).pages:
            writer.add_page(pg)
    buf = BytesIO()
    writer.write(buf)
    out = buf.getvalue()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fpath = REPORT_DIR / f"肝炎标志物_第1次_{TARGET_PLAN_ID}.pdf"
    fpath.write_bytes(out)
    print("合并完成 -> %s (%d bytes, %d 份)" % (fpath, len(out), len(parts)))

    # 校验：页数 + 关键词
    rd = PdfReader(fpath)
    full = "".join((pg.extract_text() or "") for pg in rd.pages)
    has_hep = "肝炎" in full
    has_jg = "统计结果" in full or "成绩" in full
    print("页数=%d  含'肝炎'=%s  含'统计结果/成绩'=%s" % (len(rd.pages), has_hep, has_jg))
    if not has_hep:
        raise SystemExit("校验失败：PDF 不含'肝炎'关键词，可能下错文件")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE eqa_plans SET report_file=?, updated_at=? WHERE id=?",
                (OUT_REL, time.strftime("%Y-%m-%d"), TARGET_PLAN_ID))
    conn.commit()
    cur.execute("SELECT id,program,round_no,report_file FROM eqa_plans WHERE id=?", (TARGET_PLAN_ID,))
    print("DB 已更新:", cur.fetchone())
    conn.close()
    print("OK")


if __name__ == "__main__":
    main()
