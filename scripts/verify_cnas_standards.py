import requests
BASE="http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
r=requests.post(BASE+"/auth/login",data={"username":"jinzizheng","password":"Jzz6827556"},timeout=120)
tok=r.json()["access_token"]; H={"Authorization":f"Bearer {tok}"}
lst=requests.get(BASE+"/cnas-standards",headers=H,timeout=120).json()
print(f"列表数量: {len(lst)}")
assert len(lst)==15, "列表数量异常"
# 检查排序与类别分布
cats={}
for it in lst:
    cats[it["category"]]=cats.get(it["category"],0)+1
    assert it["file_size"]>0
print("类别分布:", cats)
# 抽样预览/下载：检查 %PDF 头
for sid in [1,5,8,15]:
    pv=requests.get(BASE+f"/cnas-standards/{sid}/preview",headers=H,timeout=120)
    dl=requests.get(BASE+f"/cnas-standards/{sid}/download",headers=H,timeout=120)
    ph=pv.content[:4]==b"%PDF"; dh=dl.content[:4]==b"%PDF"
    ct_pv=pv.headers.get("Content-Type"); cd_dl=dl.headers.get("Content-Disposition")
    print(f"id={sid} preview%PDF={ph}(ct={ct_pv}) download%PDF={dh}(disp={cd_dl[:30]!r})")
    assert ph and dh, f"id={sid} 预览/下载不是合法PDF"
print("全部校验通过 ✅")
