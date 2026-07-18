"""从 3 份室间比对报告 DOCX 解析数值，回填线上 plan 1 (p2PSA) 与新建 plan 2 (IFAb+EPO)。

语义（用户更正）：
- 可比较系统 = 参比实验室 → ref1_*
- 比较系统1 = 本实验室平台1 → our_value
- 比较系统2 = 本实验室平台2 → ref2_*（可能有，亦可能空缺）

列映射（10 列表，含合并单元格）：
  c0=样本号 c1=可比较系统(参比)均值X c2/3/4=比较系统1(Y1/Y2/均值Y) c5=比较系统1偏倚
  c6/7/8=比较系统2(Y1/Y2/均值Y) c9=比较系统2偏倚

用法：DRY_RUN=1 python recover_interlab_import.py  # 只解析打印不写库
"""
import os
import json
import docx
import urllib.request
import urllib.parse

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
DRY = os.environ.get("DRY_RUN", "") == "1"

FILES = {
    "IFAb": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表IFAb.docx",
    "p2PSA": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表p2PSA.docx",
    "EPO": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表EPO.docx",
}
LABELS = ("项目", "比对实验室", "比对日期")


def find_after(row, label):
    if label not in row:
        return ""
    i = row.index(label)
    for j in range(i + 1, len(row)):
        v = row[j]
        if v and v not in LABELS:
            return v
    return ""


def norm_date(s):
    try:
        yy, mm, dd = (int(x) for x in s.split("."))
        return f"20{yy:02d}-{mm:02d}-{dd:02d}"
    except Exception:
        return s


def parse_docx(path):
    d = docx.Document(path)
    t = d.tables[0]
    rows = [[c.text.strip() for c in r.cells] for r in t.rows]
    r2 = rows[2]
    item = find_after(r2, "项目")
    ref_lab = find_after(r2, "比对实验室")
    date = norm_date(find_after(r2, "比对日期"))
    r4 = rows[4]
    sys1_machine = next((r4[j] for j in range(2, 6) if r4[j].strip()), "")
    sys2_machine = next((r4[j] for j in range(6, 10) if r4[j].strip()), "")
    ref_machine = r4[1].strip()
    levels = []
    for r in rows[6:11]:
        levels.append({
            "ref": r[1],                 # 可比较系统(参比) 均值X
            "sys1": r[2].strip() or r[4].strip(),   # 比较系统1 Y1(否则均值Y)
            "sys2": r[6].strip() or r[8].strip(),   # 比较系统2 Y1(否则均值Y)
        })
    return {
        "item": item, "ref_lab": ref_lab, "date": date,
        "sys1_machine": sys1_machine, "sys2_machine": sys2_machine,
        "ref_machine": ref_machine, "levels": levels,
    }


def build_item(rec, kind, te):
    levels = []
    for i, lv in enumerate(rec["levels"], start=1):
        levels.append({
            "level_num": i,
            "our_value": lv["sys1"],
            "ref1_y1": lv["ref"], "ref1_y2": "", "ref1_mean": lv["ref"],
            "ref2_y1": lv["sys2"], "ref2_y2": "", "ref2_mean": lv["sys2"],
        })
    return {"item": rec["item"], "unit": "", "te": str(te),
            "mode": "relative", "kind": kind, "note": "", "levels": levels}


def api(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    import urllib.parse
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=urllib.parse.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode(),
        method="POST")).read())["access_token"]

    recs = {k: parse_docx(v) for k, v in FILES.items()}
    for k, v in recs.items():
        print(f"\n=== {k} ===")
        print(f"  item={v['item']}  ref_lab={v['ref_lab']}  date={v['date']}")
        print(f"  可比较系统(参比)机器={v['ref_machine']}  比较系统1={v['sys1_machine']}  比较系统2={v['sys2_machine']}")
        for lv in v["levels"]:
            print(f"  水平: 参比={lv['ref']!r}  比较系统1={lv['sys1']!r}  比较系统2={lv['sys2']!r}")

    if DRY:
        print("\n[DRY_RUN] 未写库。")
        return

    # ---- plan 1 = p2PSA (中科院肿瘤医院 / DxI800-4 / 2026-06-23) ----
    p2 = build_item(recs["p2PSA"], "定量", 30)
    api("PUT", "/api/v1/interlab/plans/1/results", tok, {"items": [p2]})
    api("PUT", "/api/v1/interlab/plans/1", tok, {"compared_instrument2": ""})
    print("\nplan 1 (p2PSA) results saved")

    # ---- plan 2 = IFAb(定性) + EPO(定量) (安贞医院 / DxI800-急诊 / 2026-06-22) ----
    ifab = build_item(recs["IFAb"], "定性", 0)
    epo = build_item(recs["EPO"], "定量", 30)
    sys2 = recs["IFAb"]["sys2_machine"]  # DxI800-线上3号机
    plan2 = {
        "year": 2026, "half": 1, "instrument_id": 73,
        "reference_lab": "安贞医院(通州院区)", "compared_instrument2": sys2,
        "compared_at": "2026-06-22",
        "operator": "金子铮", "reviewer": "杨静",
        "summary": "使用5例样本与安贞医院(通州院区)实验室进行室间比对， 一致性可接受。",
        "conclusion": "可接受", "status": "draft",
        "items": [
            {"item": "IFAb", "unit": "", "te": "0", "mode": "relative", "kind": "定性"},
            {"item": "EPO", "unit": "", "te": "30", "mode": "relative", "kind": "定量"},
        ],
        "auto_fill": False,
    }
    created = api("POST", "/api/v1/interlab/plans", tok, plan2)
    pid2 = created["id"]
    print(f"\nplan 2 created id={pid2} (compared_instrument2={sys2})")
    api("PUT", f"/api/v1/interlab/plans/{pid2}/results", tok, {"items": [ifab, epo]})
    print(f"plan 2 (IFAb+EPO) results saved")

    # 生成报告
    api("POST", "/api/v1/interlab/plans/1/report/generate", tok)
    api("POST", f"/api/v1/interlab/plans/{pid2}/report/generate", tok)
    print("reports generated")


if __name__ == "__main__":
    main()
