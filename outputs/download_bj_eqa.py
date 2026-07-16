#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载北京市临床检验中心室间质评成绩 PDF，并关联到本地 eqa_plans 表（org=北京市, year=2026）。

逻辑要点：
- 官网 corelab.clinet.com.cn 的成绩列表页被 safedog WAF 拦截 HeadlessChrome UA，必须用桌面 UA + 登录 cookie 直连。
- 列表 URL：desktop/pdfptscoretitle.asp?t_id=4731&cclname=<GBK编码的"北京市临床检验中心">&SpecType=
- 每个项目有两类报告（链接文字）：
    * 「统计汇总表」  -> 路径 /汇总/   （本室成绩汇总，即原"汇总页"）
    * 「统计结果表」  -> 路径 /定量/ 或 /定性/ （全部参评实验室的原始结果/统计分布）
  本脚本对匹配到的 plan **两份都抓，合并成一份 PDF** 作为 report_file（超集，含成绩+统计）。
- 按 (program, round_no) 在 eqa_plans(北京市/2026) 定位；目前官网仅第1次出分，故只匹配 round_no=第1次。
- 默认跳过已有 report_file 的 plan（可重跑）；加 --force 强制重新下载并合并（覆盖）。
- 仅写 report_file（结果回报），不置 returned（已上报为独立标记）。
- ⚠️ REPORT_DIR 必须 = BASE_DIR/data/eqa_reports，与线上 EQA_REPORT_DIR=DATA_DIR/eqa_reports 保持一致，否则前端预览 404。
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

BASE_DIR = Path(__file__).resolve().parents[1]  # d:/workbuddyprojects/网页版-生免速查工具
DB_PATH = BASE_DIR / "data" / "app.db"
REPORT_DIR = BASE_DIR / "data" / "eqa_reports"  # 必须与线上 EQA_REPORT_DIR=DATA_DIR/eqa_reports 一致
COOKIE_FILE = BASE_DIR / "outputs" / "bj_cookies.txt"
LINKS_JSON = BASE_DIR / "outputs" / "eqa_bj_links.json"

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
LIST_URL = ("https://www.clinet.com.cn/clinetbusiness/hospital/desktop/"
            "pdfptscoretitle.asp?t_id=4731&cclname={ccl}&SpecType=")

# DB program(北京市) -> 北京官网项目编码（已核对 2026 第1次）
PROGRAM_TO_CODE = {
    "常规化学A": "01",
    "肝炎标志物": "21",
    "内分泌": "04",
    "肿瘤标志物A": "05",
    "凝血试验": "11",
    "糖化白蛋白": "85",
    "感染性疾病血清学标志物系列B": "86",
    "感染性疾病血清学标志物系列C": "87",
    "感染性疾病抗原抗体快速检测": "88",
    "血清降钙素原": "89",
    "中孕期母血清产前筛查": "D3",
    "细胞因子": "E7",
}
# 注：本列表当前未被 main() 使用（仅作历史参考）。
# 肝炎标志物(plan id=88/89) 北京官网编码=21；其统计结果表路径为 /定性/（脚本已用
# links.get("定量") or links.get("定性") 兼容）。第2次成绩官网成绩页尚未出分，故本脚本
# 仍仅匹配 round_no=第1次；待发布后需放开该限制才会被抓取。
# 以下为北京官网确有、但本室北京市 EQA 清单未纳入的项目（历史上用于标注"不关联"）：
UNMATCHED_PROGRAMS = [
    "临床常规化学", "全血细胞计数", "尿液化学分析", "血细胞形态学", "血型",
    "核酸检测（病毒学）", "核酸检测（非病毒学）", "北京市临床微生物",
    "尿沉渣形态学", "快速CRP检测", "粪便隐血试验", "尿HCG", "EB病毒核酸检测",
    "巨细胞病毒核酸检测", "流式细胞分析-淋巴细胞亚群", "新型冠状病毒核酸检测",
    "粪便形态学检查", "白细胞介素6（IL-6）",
]


def load_cookie():
    if not COOKIE_FILE.exists():
        raise FileNotFoundError(f"缺少 cookie 文件：{COOKIE_FILE}，请先从浏览器导出北京会话 cookie")
    raw = COOKIE_FILE.read_text(encoding="utf-8").strip()
    jar = requests.cookies.RequestsCookieJar()
    for pair in raw.split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            jar.set(k.strip(), v.strip(), domain=".clinet.com.cn", path="/")
    return jar


def fetch_list(jar):
    ccl = urllib.parse.quote("北京市临床检验中心".encode("gbk"))
    url = LIST_URL.format(ccl=ccl)
    r = requests.get(url, cookies=jar, timeout=30,
                     headers={"User-Agent": DESKTOP_UA,
                               "Referer": "https://www.clinet.com.cn/clinetbusiness/hospital/desktop/DataAdminArea4.asp"})
    r.raise_for_status()
    return r.content.decode("gb2312", "ignore")


def parse_links(html):
    """返回 code -> {sub: href} 及完整链接列表。sub in {汇总, 定量, 定性}。"""
    by_code = {}
    all_links = []
    for m in re.finditer(r'<a\s+pname="([^"]+)"\s+href="([^"]+\.pdf[^"]*)"', html, re.I):
        pname, href = m.group(1), m.group(2)
        code = pname.rsplit("_2026_", 1)[0]  # 01 / D3 / E7 / P8
        if "/汇总/" in href:
            sub = "汇总"
        elif "/定量/" in href:
            sub = "定量"
        elif "/定性/" in href:
            sub = "定性"
        else:
            sub = "?"
        by_code.setdefault(code, {})[sub] = href
        all_links.append({"pname": pname, "code": code, "sub": sub, "href": href})
    return by_code, all_links


def safe_filename(program, round_no, idx):
    base = re.sub(r'[\\/:*?"<>|]', "_", f"{program}_{round_no}_{idx}")
    return f"{base}.pdf"


def download_pdf(href, jar):
    r = requests.get(href, cookies=jar, timeout=60,
                     headers={"User-Agent": DESKTOP_UA,
                               "Referer": "https://www.clinet.com.cn/clinetbusiness/hospital/desktop/DataAdminArea4.asp"})
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").lower()
    if "application/pdf" not in ctype and not r.content.startswith(b"%PDF"):
        raise ValueError(f"非 PDF 内容：{ctype}")
    return r.content


def merge_pdfs(datas):
    """将多份 PDF 字节合并为一份，返回 bytes。datas 为 bytes 列表。"""
    writer = PdfWriter()
    for data in datas:
        reader = PdfReader(BytesIO(data))
        for page in reader.pages:
            writer.add_page(page)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---- 线上直接导入（"直接从线上版本取值和导入"工作流）----
# 关键事实：线上库是 CFS 持久化的独立库，部署只 cp -r 报告 PDF 文件、不覆盖 app.db。
# 因此本地改 data/app.db 永远传不上线。所有读写必须直接针对线上 API。
ONLINE_BASE = os.environ.get(
    "BJ_EQA_ONLINE_BASE",
    "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com",
)
ONLINE_USER = os.environ.get("BJ_EQA_ONLINE_USER", "jinzizheng")
ONLINE_PASS = os.environ.get("BJ_EQA_ONLINE_PASS", "Jzz6827556")


def push_online(plan_id, pdf_bytes, fname):
    """把合并好的报告 PDF 直接导入线上（生产）实例：POST /api/v1/eqa-plans/report/{id}。
    线上端点会自动解析成绩/得分/合格并回填 DB，无需本地改库或部署。
    注意：API 路径不要带结尾斜杠（带斜杠会掉进 SPA 兜底路由）。"""
    s = requests.Session()
    r = s.post(f"{ONLINE_BASE}/api/v1/auth/login",
               data={"username": ONLINE_USER, "password": ONLINE_PASS}, timeout=30)
    r.raise_for_status()
    tok = r.json().get("access_token")
    h = {"Authorization": f"Bearer {tok}"}
    files = {"file": (fname, pdf_bytes, "application/pdf")}
    # 不传 result/score/qualified，交由线上端点自动解析回填
    r = s.post(f"{ONLINE_BASE}/api/v1/eqa-plans/report/{plan_id}",
               files=files, data={}, headers=h, timeout=120)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印匹配，不下载/不写库")
    parser.add_argument("--download", action="store_true", help="执行下载和入库")
    parser.add_argument("--force", action="store_true", help="强制重新下载并合并（覆盖已有 report_file）")
    parser.add_argument("--online", action="store_true",
                        help="合并后直接导入线上（生产）实例 API，而非仅写本地库+部署")
    args = parser.parse_args()

    jar = load_cookie()
    html = fetch_list(jar)
    by_code, all_links = parse_links(html)
    # 保存解析结果供核查
    LINKS_JSON.write_text(json.dumps(all_links, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"官网解析到 {len(all_links)} 条 PDF 链接，{len(by_code)} 个项目")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, program, item, round_no, report_file FROM eqa_plans WHERE year=2026 AND org='北京市'")
    plans = [dict(r) for r in cur.fetchall()]
    print(f"数据库中 北京市/2026 共 {len(plans)} 条记录")

    matched = 0
    skipped = 0
    unmatched = 0
    plan_best = {}

    for p in plans:
        code = PROGRAM_TO_CODE.get(p["program"])
        if not code:
            # 非映射项目（D-二聚体/京津冀鲁盲样/系列A/结核/sTfR 等官网无）
            print(f"  [跳过] 项目不在官网映射：{p['program']} / {p['round_no']} (id={p['id']})")
            skipped += 1
            continue
        if p["round_no"] != "第1次":
            print(f"  [跳过] 官网仅第1次出分：{p['program']} / {p['round_no']} (id={p['id']})")
            skipped += 1
            continue
        links = by_code.get(code)
        if not links:
            print(f"  [未匹配] 官网无该项目编码 {code}：{p['program']} (id={p['id']})")
            unmatched += 1
            continue
        summary_href = links.get("汇总")            # 统计汇总表（已抓的"汇总页"）
        result_href = links.get("定量") or links.get("定性")  # 统计结果表
        if not summary_href and not result_href:
            print(f"  [未匹配] 项目 {code} 无可用 PDF：{p['program']} (id={p['id']})")
            unmatched += 1
            continue
        matched += 1
        plan_best[p["id"]] = (p, summary_href, result_href)

    print(f"\n匹配目标 plan 数：{len(plan_best)}")
    for pid, (p, summary_href, result_href) in sorted(plan_best.items()):
        flag = " [已有report，将跳过]" if (p.get("report_file") and not args.force) else ""
        parts = []
        if summary_href: parts.append("汇总")
        if result_href: parts.append("统计结果表")
        print(f"  plan_id={pid} {p['program']}/{p['round_no']} <- 合并[{'+'.join(parts)}]{flag}")

    if not args.download:
        print(f"\n[dry-run] 汇总：匹配 {len(plan_best)} / 跳过 {skipped} / 未匹配 {unmatched}")
        conn.close()
        return

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    update_sql = "UPDATE eqa_plans SET report_file=?, updated_at=? WHERE id=?"
    updated = 0
    for pid, (p, summary_href, result_href) in sorted(plan_best.items()):
        if p.get("report_file") and not args.force:
            print(f"  plan_id={pid} 已有 report_file，跳过（--force 可重新合并）")
            continue
        fname = safe_filename(p["program"], p["round_no"], pid)
        fpath = REPORT_DIR / fname
        rel_path = f"eqa_reports/{fname}"
        parts = []
        try:
            if summary_href:
                parts.append(("汇总", download_pdf(summary_href, jar)))
            if result_href:
                parts.append(("统计结果表", download_pdf(result_href, jar)))
            if not parts:
                print(f"  [失败] plan_id={pid}：无可用 PDF")
                continue
            data = parts[0][1] if len(parts) == 1 else merge_pdfs([b for _, b in parts])
            with open(fpath, "wb") as f:
                f.write(data)
            print(f"  [下载+合并] {'+'.join(l for l, _ in parts)} -> {len(data)} bytes -> {fpath}")
            if args.online:
                try:
                    res = push_online(pid, data, fname)
                    print(f"  [线上导入] plan_id={pid} report_file={res.get('report_file')} "
                          f"result={res.get('result')} qualified={res.get('qualified')}")
                except Exception as e:
                    print(f"  [线上导入失败] plan_id={pid}：{e}")
        except Exception as e:
            print(f"  [失败] plan_id={pid}：{e}")
            continue
        cur.execute(update_sql, (rel_path, time.strftime("%Y-%m-%d"), pid))
        updated += 1
        time.sleep(0.5)

    conn.commit()
    print(f"\n共更新 {updated} 条数据库记录")
    conn.close()
    print(f"\n汇总：匹配 {len(plan_best)} / 跳过 {skipped} / 未匹配 {unmatched}")


if __name__ == "__main__":
    main()
