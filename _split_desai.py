import json, urllib.request, urllib.parse, sys, os
from collections import defaultdict

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
USER = "jinzizheng"; PASS = "Jzz6827556"
PUSH = "--push" in sys.argv
IMMUNO = {"APOA1","APOB","ASO","IgA","IgG","IgM","LPa","RF"}

def req(method, path, token=None, form=None, json_body=None):
    url = BASE + path; data=None; headers={"Accept":"application/json"}
    if token: headers["Authorization"]=f"Bearer {token}"
    if form is not None:
        data=urllib.parse.urlencode(form).encode(); headers["Content-Type"]="application/x-www-form-urlencoded"
    if json_body is not None:
        data=json.dumps(json_body).encode(); headers["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(r,timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode())

def login():
    st,b=req("POST","/api/v1/auth/login",form={"username":USER,"password":PASS})
    return b["access_token"]

# ---- dry-run-only helpers to inspect ----
tok = login()
st, plans = req("GET","/api/v1/comparison/plans?group_id=1", tok)
print("group1 plans before:", [(p["id"],p["year"],p["half"],p["compared_at"],p["status"]) for p in plans["items"]])

st, g1 = req("GET","/api/v1/comparison/groups/1", tok)
print("group1 levels:", g1["levels"], "ref_inst:", g1["reference_instrument_id"], "insts:", g1["instrument_ids"])

st, p5 = req("GET","/api/v1/comparison/plans/5", tok)
print("plan5 meta:", {k:p5[k] for k in ("year","half","compared_at","status","operator","reviewer","summary","conclusion","handle_plan","only_uncompared")})

st, res = req("GET","/api/v1/comparison/plans/5/results", tok)
quant = res.get("quant", [])
seen=defaultdict(set)
for r in quant: seen[r["item"]].add(r["level"])
chem=[]; immu=[]
for r in quant:
    if r["item"] in IMMUNO: immu.append(r)
    else: chem.append(r)
print(f"plan5 quant rows: {len(quant)}  chem={len(chem)}  immuno={len(immu)}")
print("immuno items:", sorted(IMMUNO & set(seen.keys())))
print("chem items:", sorted(set(seen.keys()) - IMMUNO))
# backup
os.makedirs("outputs", exist_ok=True)
with open("outputs/plan5_backup_pre_split.json","w",encoding="utf-8") as f:
    json.dump({"plan":p5,"group1":g1,"quant":quant}, f, ensure_ascii=False, indent=2)
print("backup -> outputs/plan5_backup_pre_split.json")

if not PUSH:
    print("\n[DRY RUN] rerun with --push to apply: create group+plan for 德赛, revert group1 to 3 levels, remove immuno from plan5, regenerate both reports")
    sys.exit(0)

# ---- PUSH ----
# 1) extract immuno items config from group1
g1_items = g1["items"]
immuno_cfg = [it for it in g1_items if it["name"] in IMMUNO]
# 2) create new group for 德赛 (levels=5)
new_group = {
    "name":"生化分析仪（德赛项目）",
    "category":"定量",
    "form_code":g1["form_code"],
    "form_title":g1["form_title"],
    "instrument_ids":[67,68,5],
    "reference_instrument_id":68,
    "levels":5,
    "items":[{"name":it["name"],"label":it.get("label",""),"te":it.get("te","0"),
              "mode":it.get("mode","relative"),"instrument_ids":[67,68,5]} for it in immuno_cfg],
    "sample_desc":"5个不同浓度水平的室间质评样本",
    "note":"德赛项目（260617）室内比对，5水平",
}
st,ng=req("POST","/api/v1/comparison/groups", tok, json_body=new_group)
new_gid=ng["id"]; print("created group", new_gid, ng["name"])

# 3) create new plan in new group
new_plan = {
    "group_id":new_gid, "year":2026, "half":1,
    "form_code":g1["form_code"], "form_title":g1["form_title"],
    "compared_at":"2026-06-17", "operator":p5.get("operator","") or "吕文娟",
    "reviewer":"金子铮", "status":"done",
    "only_uncompared":False,
}
st,np_=req("POST","/api/v1/comparison/plans", tok, json_body=new_plan)
new_pid=np_["id"]; print("created plan", new_pid, "year",np_["year"],"half",np_["half"])

# 4) PUT immuno data into new plan
immuno_rows=[{"item":r["item"],"level":r["level"],"reference_value":r["reference_value"],"values":r["values"]} for r in immu]
st,rp=req("PUT",f"/api/v1/comparison/plans/{new_pid}/results", tok, json_body={"quant":immuno_rows,"qual":[]})
print("PUT immuno results:", st, rp)

# 5) revert group1: levels=3, remove immuno items
g1_items_keep=[it for it in g1_items if it["name"] not in IMMUNO]
st,rg=req("PUT","/api/v1/comparison/groups/1", tok, json_body={"levels":3,"items":g1_items_keep})
print("revert group1 levels=3, items", len(g1_items_keep))

# 6) delete plan5 (cascade), recreate chemistry-only
st,dd=req("DELETE",f"/api/v1/comparison/plans/5", tok); print("delete plan5:", st, dd)
recreate={
    "group_id":1,"year":p5["year"],"half":p5["half"],
    "form_code":p5["form_code"],"form_title":p5["form_title"],
    "compared_at":p5["compared_at"],"operator":p5.get("operator",""),"reviewer":"金子铮",
    "summary":p5.get("summary",""),"conclusion":p5.get("conclusion",""),
    "handle_plan":p5.get("handle_plan",""),"status":p5["status"],"only_uncompared":bool(p5.get("only_uncompared",False)),
}
st,r5=req("POST","/api/v1/comparison/plans", tok, json_body=recreate)
new_p5=r5["id"]; print("recreated plan5 as id", new_p5)
chem_rows=[{"item":r["item"],"level":r["level"],"reference_value":r["reference_value"],"values":r["values"]} for r in chem]
st,rp=req("PUT",f"/api/v1/comparison/plans/{new_p5}/results", tok, json_body={"quant":chem_rows,"qual":[]})
print("PUT chem results:", st, rp)

# 7) regenerate reports
st,gr=req("POST",f"/api/v1/comparison/plans/{new_pid}/report/generate", tok); print("gen 德赛 report:", st, gr.get("report_path"))
st,gr=req("POST",f"/api/v1/comparison/plans/{new_p5}/report/generate", tok); print("gen chem report:", st, gr.get("report_path"))

# 8) verify
st,plans=req("GET","/api/v1/comparison/plans", tok)
print("\nALL plans now:")
for p in plans["items"]:
    print(f"  id={p['id']} group={p['group_id']} {p['year']}H{p['half']} {p['compared_at']} items={p['compared_count']}")
