"""从 3 份室间比对报告 DOCX 解析数值，回填线上 plan 1 (p2PSA) 与新建 plan 2 (IFAb+EPO)。

语义（用户更正）：
- 可比较系统 = 参比实验室 → ref1_*
- 比较系统1 = 本实验室平台1 → our_value
- 比较系统2 = 本实验室平台2 → ref2_* (临时存放，多平台改造后迁移)
"""
import json
import docx
import urllib.request

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
FILES = {
    "IFAb": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表IFAb.docx",
    "p2PSA": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表p2PSA.docx",
    "EPO": r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果/BG-SM-CZ-019-定量项目室间比对结果记录及分析报告表EPO.docx",
}


def parse_docx(path):
    d = docx.Document(path)
    t = d.tables[0]
    rows = [[c.text.strip() for c in r.cells] for r in t.rows]
    # 基本信息
    item = rows[2][1]
    ref_lab = rows[3][4]
    date = rows[3][8] or rows[3][9]
    # 数据行 = 样本 1-5 (index 6..10)
    levels = []
    for r in rows[6:11]:
        levels.append({
            "ref": r[1],       # 可比较系统 均值X (参比)
            "p1_y1": r[2],     # 比较系统1 Y1 (本实验室平台1)
            "p1_y2": r[3],
            "p1_mean": r[4],
            "p1_bias": r[5],
            "p2_y1": r[6],     # 比较系统2 Y1 (本实验室平台2)
            "p2_y2": r[7],
            "p2_mean": r[8],
            "p2_bias": r[9],
        })
    return {"item": item, "ref_lab": ref_lab, "date": date, "levels": levels}


def build_item(rec, kind, te):
    levels = []
    for i, lv in enumerate(rec["levels"], start=1):
        levels.append({
            "level_num": i,
            "our_value": lv["p1_y1"],          # 比较系统1 → 我室值
            "ref1_y1": lv["ref"],               # 可比较系统 → 参比 Y1
            "ref1_y2": "",
            "ref1_mean": lv["ref"],             # 参比 均值
            "ref2_y1": lv["p2_y1"],             # 比较系统2 → 暂存 ref2 (多平台改造后迁移)
            "ref2_y2": "",
            "ref2_mean": lv["p2_y1"],
        })
    return {
        "item": rec["item"], "unit": "", "te": str(te),
        "mode": "relative", "kind": kind, "note": "",
        "levels": levels,
    }


def api(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def main():
    # 登录
    import urllib.parse
    login_body = urllib.parse.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(BASE + "/api/v1/auth/login", data=login_body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.loads(resp.read())["access_token"]

    recs = {k: parse_docx(v) for k, v in FILES.items()}
    for k, v in recs.items():
        print(f"{k}: item={v['item']} ref={v['ref_lab']} date={v['date']} levels={len(v['levels'])}")

    # plan 1 = p2PSA (中科院肿瘤医院/DxI800-4/6.23，与线上 plan1 元数据一致)
    p2 = build_item(recs["p2PSA"], "定量", 30)
    api("PUT", "/api/v1/interlab/plans/1/results", tok, {"items": [p2]})
    print("plan 1 (p2PSA) results saved")

    # plan 2 = IFAb + EPO (安贞医院/DxI800-急诊/6.22)
    ifab = build_item(recs["IFAb"], "定性", 0)
    epo = build_item(recs["EPO"], "定量", 30)
    plan2 = {
        "year": 2026, "half": 1, "instrument_id": 73,
        "reference_lab": "安贞医院(通州院区)", "compared_at": "2026-06-22",
        "operator": "金子铮", "reviewer": "杨静",
        "summary": "使用5例样本与安贞医院(通州院区)实验室进行室间比对， 一致性可接受。",
        "conclusion": "可接受", "status": "draft",
        "items": [
            {"item": "IFAb", "unit": "", "te": "0", "mode": "relative", "kind": "定性"},
            {"item": "EPO", "unit": "", "te": "30", "mode": "relative", "kind": "定量"},
        ],
        "auto_fill": False,
    }
    created = json.loads(api("POST", "/api/v1/interlab/plans", tok, plan2))
    pid2 = created["id"]
    print(f"plan 2 created id={pid2}")
    api("PUT", f"/api/v1/interlab/plans/{pid2}/results", tok, {"items": [ifab, epo]})
    print(f"plan 2 (IFAb+EPO) results saved")

    # 生成报告
    api("POST", "/api/v1/interlab/plans/1/report/generate", tok)
    api("POST", f"/api/v1/interlab/plans/{pid2}/report/generate", tok)
    print("reports generated")


if __name__ == "__main__":
    main()
