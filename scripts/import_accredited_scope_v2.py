"""认可能力范围 v2 导入：按「更正后」xlsx 重建。

相较 v1 的关键变化（用户已更正 xlsx）：
- 许多项目新增「血浆」样品类型续行、部分项目（乙肝表面抗原 / 抗丙肝抗体）新增
  罗氏 cobas e411 仪器续行。v1 的解析器会跳过这些续行，导致血浆/额外仪器丢失。
- 本脚本把续行展开为独立样品行（按 样品类型 拆分），同一项目的多仪器用 \\n 合并到
  同一(项目,样品类型)行的 instrument_name。

关联策略（避免 replace 清空已确认的关联）：
- 按 item_name 从「现有线上数据」继承 instrument_id/instrument_name/reagent_id/
  reagent_name/method_name/method_id：chem(AU5800)、糖化(东曹)、CRP 等已确认的
  关联原样继承到该项目所有样品行（含新增的血浆行）。
- 无系统关联的（免疫/血凝）保留 xlsx 原文（仪器/试剂长文本），instrument_id/reagent_id 留空。
- 校准品 / 分析性能 5 项 / 样品类型等「内容字段」一律以更正后的 xlsx 为准。

用法：
  python import_accredited_scope_v2.py            # dry-run 预览
  APPLY=1 python import_accredited_scope_v2.py    # 真正重建（replace=true）
"""
from __future__ import annotations
import os, json, re, urllib.request, urllib.parse, openpyxl

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
USERNAME, PASSWORD = "jinzizheng", "Jzz6827556"
XLSX = r"D:/民航总医院/15189/生免认可申请附表/生免组申请认可的能力范围.xlsx"
COL = {
    "seq":1,"item_name":2,"sample_type":3,"method_name":4,
    "instrument_name":5,"reagent_name":6,"calibrator":7,
    "description":8,"remark":9,
    "perf_correctness":10,"perf_precision":11,"perf_linearity":12,
    "perf_reportable":15,"perf_other":17,
}

_tok={"v":None}
def login():
    _,l=req_raw("POST","/auth/login",{"username":USERNAME,"password":PASSWORD})
    _tok["v"]=l["access_token"]
def req_raw(method,path,data=None,token=""):
    url=BASE+path; h={"Accept":"application/json"}
    if token: h["Authorization"]=f"Bearer {token}"
    body=None
    if data is not None:
        if method=="POST" and path=="/auth/login":
            body=urllib.parse.urlencode(data).encode(); h["Content-Type"]="application/x-www-form-urlencoded"
        else:
            body=json.dumps(data,ensure_ascii=False).encode(); h["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=body,headers=h,method=method)
    try:
        resp=urllib.request.urlopen(r,timeout=120); return resp.status,json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode()[:300]
def req(method,path,data=None,token=None):
    if token is None: token=_tok["v"] or login()
    st,r=req_raw(method,path,data,token)
    if st==401: token=login(); st,r=req_raw(method,path,data,token)
    return st,r
def paged(path,size=500):
    out,page=[] ,1
    sep="&" if "?" in path else "?"
    while True:
        st,r=req("GET",f"{path}{sep}page={page}&page_size={size}")
        if st!=200: raise RuntimeError(f"{path} {st} {r}")
        items=r.get("items",[]); out+=items
        if len(items)<size or "items" not in r: break
        page+=1
    return out

def _cell(ws,row,col):
    v=ws.cell(row=row,column=col).value
    if v is None: return ""
    if isinstance(v,float) and v.is_integer(): return str(int(v))
    if isinstance(v,(int,float)): return str(v)
    return str(v).strip()

def _join(*parts):
    seen=[]; 
    for p in parts:
        for line in str(p or "").split("\n"):
            line=line.strip()
            if line and line not in seen: seen.append(line)
    return "\n".join(seen)

def parse_xlsx(path):
    wb=openpyxl.load_workbook(path,data_only=True); ws=wb.active
    items=[]; cur_l1=cur_l2=""; cur_item=None; cur_sample=None
    for r in range(3, ws.max_row+1):
        a=_cell(ws,r,COL["seq"]); b=_cell(ws,r,COL["item_name"])
        if a and not b:  # 分组行
            m=re.match(r"^([A-Z]+)\s",a); n=len(m.group(1)) if m else 0
            if n<=1: cur_l1=a; cur_l2=""
            else: cur_l2=a
            continue
        if not b:
            if not a:  # 续行
                c=_cell(ws,r,COL["sample_type"]); d=_cell(ws,r,COL["method_name"])
                e=_cell(ws,r,COL["instrument_name"]); f=_cell(ws,r,COL["reagent_name"]); g=_cell(ws,r,COL["calibrator"])
                if c:  # 新样品类型
                    # 如果续行未填写设备/试剂/校准品，继承该项目首个样品行的内容
                    # （Excel 中常有只写样品类型、其余留空的简写续行）
                    base = cur_item["samples"][0] if cur_item and cur_item["samples"] else {}
                    cur_sample={
                        "sample_type":c,
                        "method_name":d or base.get("method_name",""),
                        "instrument_name":e or base.get("instrument_name",""),
                        "reagent_name":f or base.get("reagent_name",""),
                        "calibrator":g or base.get("calibrator",""),
                    }
                    cur_item["samples"].append(cur_sample)
                else:  # 同一样品类型的附加仪器/试剂/校准品
                    if cur_sample is not None:
                        cur_sample["instrument_name"]=_join(cur_sample["instrument_name"],e)
                        cur_sample["reagent_name"]=_join(cur_sample["reagent_name"],f)
                        cur_sample["calibrator"]=_join(cur_sample["calibrator"],g)
                continue
            continue  # a 非空 b 空且非分组：跳过
        # 主项目行
        perf={k:_cell(ws,r,COL[k]) for k in ("perf_correctness","perf_precision","perf_linearity","perf_reportable","perf_other")}
        cur_item={"category_l1":cur_l1,"category_l2":cur_l2,"seq":a,"item_name":b,
                  "description":_cell(ws,r,COL["description"]),"remark":_cell(ws,r,COL["remark"]),
                  "perf":perf,"samples":[]}
        cur_sample={"sample_type":_cell(ws,r,COL["sample_type"]),
                    "method_name":_cell(ws,r,COL["method_name"]),
                    "instrument_name":_cell(ws,r,COL["instrument_name"]),
                    "reagent_name":_cell(ws,r,COL["reagent_name"]),
                    "calibrator":_cell(ws,r,COL["calibrator"])}
        cur_item["samples"].append(cur_sample)
        items.append(cur_item)
    return items

def main():
    items=parse_xlsx(XLSX)
    print(f"解析得到 {len(items)} 个主项目，展开样品行：")
    flat=[]
    for it in items:
        for s in it["samples"]:
            flat.append((it,s))
    print(f"  共 {len(flat)} 个 (项目,样品类型) 行")

    # 现有线上数据：按 item_name 继承关联
    login()
    existing=paged("/accredited-scope?page_size=5000")
    by_name={}
    for e in existing:
        by_name.setdefault(e["item_name"], e)
    print(f"  现有线上 {len(existing)} 行，可继承关联的项目名 {len(by_name)} 个")

    payload=[]
    for it,s in flat:
        ex=by_name.get(it["item_name"])
        rec={
            "category_l1":it["category_l1"],"category_l2":it["category_l2"],
            "seq":it["seq"],"item_name":it["item_name"],
            "sample_type":s["sample_type"],
            "calibrator":s["calibrator"],
            "description":it["description"],"remark":it["remark"],
            "perf_correctness":it["perf"]["perf_correctness"],
            "perf_precision":it["perf"]["perf_precision"],
            "perf_linearity":it["perf"]["perf_linearity"],
            "perf_reportable":it["perf"]["perf_reportable"],
            "perf_other":it["perf"]["perf_other"],
            "method_id":None,"method_name":"","instrument_id":None,"instrument_name":"","reagent_id":None,"reagent_name":"",
        }
        if ex:
            # 保留系统关联 ID（避免 replace 清空已有确认关联）
            rec["method_id"]=ex.get("method_id")
            rec["instrument_id"]=ex.get("instrument_id")
            rec["reagent_id"]=ex.get("reagent_id")
            # 名称文本优先使用 Excel 原始内容（含注册证号、设备编号、多仪器等），
            # 只有 Excel 为空时才回退到系统已有名称
            rec["method_name"]=s["method_name"] or ex.get("method_name") or ""
            rec["instrument_name"]=s["instrument_name"] or ex.get("instrument_name") or ""
            rec["reagent_name"]=s["reagent_name"] or ex.get("reagent_name") or ""
        else:
            rec["method_name"]=s["method_name"]
            rec["instrument_name"]=s["instrument_name"]
            rec["reagent_name"]=s["reagent_name"]
        payload.append(rec)

    # 预览
    print("\n--- 预览（前 12 行）---")
    for rec in payload[:12]:
        print(f"  [{rec['category_l2'][:6]}] {rec['seq']:>3} {rec['item_name'][:12]:<12} | {rec['sample_type']:<16} | 方法:{rec['method_name'][:10]:<10} | 仪id:{rec['instrument_id']} 试id:{rec['reagent_id']}")
    # 统计
    with_inst=sum(1 for r in payload if r["instrument_id"])
    with_reag=sum(1 for r in payload if r["reagent_id"])
    st_types=sorted(set(r["sample_type"] for r in payload))
    print(f"\n统计：总行数={len(payload)}，有仪器关联={with_inst}，有试剂关联={with_reag}")
    print(f"  样品类型取值：{st_types}")

    APPLY=os.environ.get("APPLY")=="1"
    print(f"\n{'== APPLY 模式 ==' if APPLY else '== DRY-RUN 模式(未落库) =='}")
    if APPLY:
        st,r=req("POST","/accredited-scope/batch?replace=true",payload)
        print("  批量导入返回:",st,r)
        # 验证
        after=paged("/accredited-scope?page_size=5000")
        print(f"  导入后线上条数: {len(after)}")

if __name__=="__main__":
    main()
