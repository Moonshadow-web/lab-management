import os, sys, requests

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
FOLDER = r"C:\Users\81526\WorkBuddy\2026-08-05-01-40-06\cnas_standards"
APPLY = os.environ.get("APPLY") == "1"

r = requests.post(BASE + "/auth/login", data={"username": "jinzizheng", "password": "Jzz6827556"}, timeout=120)
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# 先查已有，避免重复播种（幂等：按 original_filename 去重）
existing = set()
try:
    page = 1
    while True:
        rr = requests.get(BASE + "/cnas-standards", params={"page": page, "page_size": 200}, headers=H, timeout=120)
        j = rr.json()
        for it in j:
            existing.add(it.get("original_filename"))
        if len(j) < 200:
            break
        page += 1
except Exception as e:
    print("查询已有记录失败(忽略):", e)

files = sorted(f for f in os.listdir(FOLDER) if f.lower().endswith(".pdf"))
print(f"文件夹内 PDF 数: {len(files)}，已存在 {len(existing)} 个")

if not APPLY:
    print("[DRY_RUN] 待上传:", [f for f in files if f not in existing] or "（全部已存在）")
    sys.exit(0)

ok = fail = skip = 0
for fn in files:
    path = os.path.join(FOLDER, fn)
    if fn in existing:
        print(f"  跳过(已存在) {fn}")
        skip += 1
        continue
    with open(path, "rb") as fh:
        content = fh.read()
    rr = requests.post(
        BASE + "/cnas-standards/upload",
        files={"file": (fn, content, "application/pdf")},
        headers=H, timeout=300,
    )
    if rr.ok:
        d = rr.json()
        print(f"  上传成功 {fn} → id={d['id']} code={d['code']!r} name={d['name']!r} cat={d['category']}")
        ok += 1
    else:
        print(f"  上传失败 {fn}: {rr.status_code} {rr.text[:200]}")
        fail += 1

print(f"\n结果: 新增={ok}  跳过={skip}  失败={fail}")
