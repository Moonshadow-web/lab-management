"""校验：/reagent/template 是否返回 default_batch_no / default_expiry_date。"""
import json
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
tok = open("/tmp/tok").read().strip()


def get(path):
    req = urllib.request.Request(H + path, headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=180))


for lib in ("免疫", "生化凝血"):
    d = get("/api/v1/reagent/template?library=" + urllib.parse.quote(lib))
    t = d.get(lib) or {}
    entries = []
    for g in t.get("by_project") or []:
        entries += g.get("items") or []
    for g in t.get("by_instrument") or []:
        entries += g.get("items") or []
    entries += t.get("controls") or []
    withb = [e for e in entries if e.get("default_batch_no")]
    print(f"[{lib}] 模板条目 {len(entries)}，带默认批号 {len(withb)}")
    for iid in (64, 18, 22, 92, 74):
        hit = [e for e in entries if e["item_id"] == iid]
        if hit:
            e = hit[0]
            print(
                f"   item{iid} {e['name'][:24]:<26} 批号={e.get('default_batch_no')!r} "
                f"效期={e.get('default_expiry_date')!r} 库存={e['current_stock']}"
            )
