#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载国家卫健委临检中心室间质评成绩 PDF，并关联到本地 eqa_plans 表。

逻辑要点：
- 按 (program, round_no) 在 eqa_plans(卫健委/2026) 中定位目标 plan。
- 多个 PDF 链接命中同一 plan 时，仅取最佳一条（PDF 原始项目名与数据库 program 精确同名者优先）。
- 若 plan 已有 report_file，则跳过（不覆盖、不重复下载），保证可重跑。
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parents[1]  # d:/workbuddyprojects/网页版-生免速查工具
DB_PATH = BASE_DIR / "data" / "app.db"
REPORT_DIR = BASE_DIR / "backend" / "data" / "eqa_reports"
LINKS_FILE = BASE_DIR / "outputs" / "eqa_nccl_links.json"
AUTH_FILE = Path("C:/Users/81526/.workbuddy/binaries/node/workspace/auth.json")

# PDF 项目名称 -> 数据库 program 字段（规范化后）
PDF_TO_DB = {
    "常规化学A": "常规化学A",
    "常规化学B": "常规化学B",
    "血气和酸碱分析": "血气和酸碱分析",
    "血清治疗药物监测": "血清治疗药物监测",
    "内分泌": "内分泌",
    "特殊蛋白": "特殊蛋白",
    "糖化血红蛋白": "糖化血红蛋白",
    "凝血试验": "凝血试验",
    "中孕期母血清产前筛查": "中孕期母血清产前筛查",
    "优生优育免疫学测定": "优生优育免疫学测定",
    "脂类A": "脂类A",
    "脂类B": "脂类B",
    "心肌标志物": "心肌标志物",
    "感染性疾病抗原抗体快速检测": "感染性疾病抗原抗体快速检测",
    "脑脊液生化检测": "脑脊液生化",
    "感染性疾病血清学标志物系列A": "感染性疾病血清学标志物系列A",
    "感染性疾病血清学标志物系列B": "感染性疾病血清学标志物系列B",
    "感染性疾病血清学标志物系列C": "感染性疾病血清学标志物系列C",
    "尿液化学分析": "尿液定量生化",  # 网站名与数据库名不同
    "尿液定量生化": "尿液定量生化",
    "心衰标志物（原脑钠肽/N末端前脑钠肽）": "心衰标志物",
    "半胱氨酸蛋白酶抑制剂C": "半胱氨酸蛋白酶抑制剂C",
    "血清蛋白电泳": "血清蛋白电泳",
    "D-二聚体检测": "D-二聚体检测",
    "尿液蛋白标志物Ⅰ": "尿液蛋白标志物Ⅰ",
    "血清降钙素原": "血清降钙素原",
    "抗凝蛋白检测": "抗凝蛋白",
    "纤维蛋白（原）降解产物检测": "纤维蛋白（原）降解产物检测",
    "糖化白蛋白": "糖化白蛋白",
    "甲状腺功能检测": "甲状腺功能检测",
    "细胞因子": "细胞因子",
    "肝纤维化血清学指标": "肝纤维化血清学指标",
    "骨代谢标志物": "骨代谢标志物",
    "血清淀粉样蛋白A": "血清淀粉样蛋白A",
    "抗缪勒管激素": "抗缪勒管激素",          # AMH（卫健委 plan id=74/75）
    "肿瘤标志物A": "肿瘤标志物A",            # 卫健委 plan id=80/81
}

# 忽略的项目（IQC、特殊项目、不在本室 47 项清单内）
SKIP_PATTERNS = [
    re.compile(r"便携式血糖检测仪"),
    re.compile(r"临床检验常规化学专业患者数据实验室间比对"),
    re.compile(r"临床微生物学"),
    re.compile(r"寄生虫形态学检查"),
    re.compile(r"抗核抗体"),
    re.compile(r"人类白细胞抗原"),
    re.compile(r"抗环瓜氨酸肽"),
    re.compile(r"巨细胞病毒核酸"),
    re.compile(r"氯吡格雷药物代谢基因"),
    re.compile(r"他莫昔芬药物代谢基因"),
    re.compile(r"EB病毒核酸"),
    re.compile(r"叶酸代谢基因"),
    re.compile(r"新型冠状病毒核酸"),
    re.compile(r"真菌感染检测项目"),
    re.compile(r"肺炎支原体核酸"),
    re.compile(r"酵母样真菌鉴定"),
    re.compile(r"外周血/骨髓涂片"),
    re.compile(r"血细胞形态识别"),
    re.compile(r"流式细胞分析"),
    re.compile(r"血型"),
    re.compile(r"全血细胞计数正确度验证"),
]


def parse_name(name: str):
    """从 PDF 名称解析项目、轮次。"""
    name = name.replace("\t", " ").strip()
    m = re.search(r"第(\d+)次", name)
    if not m:
        return None, None
    round_no = f"第{m.group(1)}次"
    m2 = re.search(r"\d{4}年(.+?)第\d+次", name)
    if not m2:
        return None, None
    project = m2.group(1).strip()
    return project, round_no


def load_cookies():
    if not AUTH_FILE.exists():
        raise FileNotFoundError(f"缺少认证文件：{AUTH_FILE}")
    auth = json.load(open(AUTH_FILE, encoding="utf-8"))
    jar = requests.cookies.RequestsCookieJar()
    for c in auth.get("cookies", []):
        jar.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path"))
    return jar


def safe_filename(project: str, round_no: str, url: str, idx: int) -> str:
    ext = os.path.splitext(url.split("?")[0])[-1] or ".pdf"
    base = re.sub(r'[\\/:*?"<>|]', "_", f"{project}_{round_no}_{idx}")
    return f"{base}{ext}"


def should_skip(project: str, name: str) -> bool:
    if project not in PDF_TO_DB:
        return True
    for pat in SKIP_PATTERNS:
        if pat.search(name):
            return True
    return False


def download_pdf(href, jar):
    r = requests.get(href, cookies=jar, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").lower()
    if "application/pdf" not in ctype and not r.content.startswith(b"%PDF"):
        raise ValueError(f"非 PDF 内容：{ctype}")
    return r.content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印匹配，不下载/不写库")
    parser.add_argument("--download", action="store_true", help="执行下载和入库")
    args = parser.parse_args()

    if not LINKS_FILE.exists():
        print(f"链接文件不存在：{LINKS_FILE}")
        sys.exit(1)

    links = json.load(open(LINKS_FILE, encoding="utf-8"))
    print(f"读取到 {len(links)} 条 PDF 链接")

    jar = load_cookies()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, program, item, round_no, report_file FROM eqa_plans WHERE year=2026 AND org='卫健委'")
    plans = [dict(r) for r in cur.fetchall()]
    print(f"数据库中 卫健委/2026 共 {len(plans)} 条记录")

    # (program, round_no) -> [plan...]
    plan_map = {}
    for p in plans:
        key = (p["program"], p["round_no"])
        plan_map.setdefault(key, []).append(p)

    # plan_id -> {links:[...], best:idx}
    plan_links = {}

    matched = 0
    unmatched = 0
    skipped = 0

    for idx, row in enumerate(links, 1):
        name = row["name"]
        href = row["href"]
        project, round_no = parse_name(name)
        if not project:
            print(f"[{idx}] 无法解析轮次：{name}")
            unmatched += 1
            continue
        if should_skip(project, name):
            print(f"[{idx}] 跳过：{project} / {round_no} ({name[:36]}...)")
            skipped += 1
            continue
        db_program = PDF_TO_DB[project]
        key = (db_program, round_no)
        candidates = plan_map.get(key)
        if not candidates:
            print(f"[{idx}] 未匹配到数据库：{db_program} / {round_no}")
            unmatched += 1
            continue

        # 选候选 plan：优先 item==program 且未设 report_file
        chosen = None
        for c in candidates:
            if c["item"] == c["program"] and not c.get("report_file"):
                chosen = c
                break
        if not chosen:
            chosen = min(candidates, key=lambda c: (bool(c.get("report_file")), c["id"]))

        matched += 1
        entry = plan_links.setdefault(chosen["id"], {"plan": chosen, "links": []})
        entry["links"].append((idx, project, name, href))

    # 每个 plan 仅取最佳链接：原始项目名与 db program 精确同名者优先
    plan_best = {}
    for pid, entry in plan_links.items():
        prog = entry["plan"]["program"]
        best = None
        for (idx, project, name, href) in entry["links"]:
            if project == prog:  # 精确同名优先
                best = (idx, project, name, href)
                break
        if best is None:
            best = entry["links"][0]
        plan_best[pid] = (entry["plan"], best)

    print(f"\n匹配去重后目标 plan 数：{len(plan_best)}（原始命中 {matched} 条链接）")
    for pid, (plan, best) in sorted(plan_best.items()):
        flag = " [已存在report，将跳过]" if plan.get("report_file") else ""
        print(f"  plan_id={pid} {plan['program']}/{plan['round_no']} <- 选用PDF#{best[0]} {best[1]}{flag}")

    if not args.download:
        print(f"\n[dry-run] 汇总：匹配去重 {len(plan_best)} / 跳过 {skipped} / 未匹配 {unmatched}")
        conn.close()
        return

    # 仅写入成绩报告 PDF（结果回报），不动 returned（已上报为独立标记，由用户手动标记）
    update_sql = "UPDATE eqa_plans SET report_file=?, updated_at=? WHERE id=?"
    updated = 0
    for pid, (plan, best) in sorted(plan_best.items()):
        if plan.get("report_file"):
            print(f"  plan_id={pid} 已有report_file，跳过下载")
            continue
        idx, project, name, href = best
        fname = safe_filename(project, plan["round_no"], href, idx)
        fpath = REPORT_DIR / fname
        rel_path = f"eqa_reports/{fname}"
        try:
            data = download_pdf(href, jar)
            with open(fpath, "wb") as f:
                f.write(data)
            print(f"[{idx}] 下载 {len(data)} bytes -> {fpath}")
        except Exception as e:
            print(f"[{idx}] 下载失败（plan_id={pid}）：{e}")
            continue
        cur.execute(update_sql, (rel_path, time.strftime("%Y-%m-%d"), pid))
        updated += 1
        time.sleep(0.3)

    conn.commit()
    print(f"\n共更新 {updated} 条数据库记录")
    conn.close()
    print(f"\n汇总：匹配去重 {len(plan_best)} / 跳过 {skipped} / 未匹配 {unmatched}")


if __name__ == "__main__":
    main()
