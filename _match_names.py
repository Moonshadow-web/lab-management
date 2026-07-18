import os, openpyxl, urllib.request, urllib.parse, json
BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
def req(method, path, tok=None):
    h = {"Content-Type": "application/json"}
    if tok: h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(BASE + path, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, json.loads(resp.read())
r = urllib.request.Request(BASE + "/auth/login", data=urllib.parse.urlencode({"username":"jinzizheng","password":"Jzz6827556"}).encode(), headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
TOK = json.loads(urllib.request.urlopen(r, timeout=30).read())["access_token"]

# 生化 Excel items (main sheet col1 of data rows 5..112)
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
wb = openpyxl.load_workbook(os.path.join(d, "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx"), data_only=True)
ws = wb["生化分析仪比对"]
excel_items = []
for rr in range(5, 113):
    v = ws.cell(row=rr, column=1).value
    if v is not None and str(v).strip():
        excel_items.append(str(v).strip())
print("EXCEL 生化 items (%d):" % len(excel_items))
print(excel_items)
print()
# group 1 items
st, g = req("GET", "/comparison/groups/1", TOK)
grp_items = [it.get("name") for it in g.get("items", [])]
print("GROUP1 items (%d):" % len(grp_items))
print(grp_items)
