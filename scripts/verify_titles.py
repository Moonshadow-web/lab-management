import requests
BASE="http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
r=requests.post(BASE+"/auth/login",data={"username":"jinzizheng","password":"Jzz6827556"},timeout=120)
tok=r.json()["access_token"]
items=[]
page=1
while True:
    rr=requests.get(BASE+"/documents",params={"page":page,"page_size":200},headers={"Authorization":f"Bearer {tok}"},timeout=120)
    j=rr.json(); items+=j["items"]
    if page*200>=j.get("total",0) or not j["items"]: break
    page+=1
for N in ["SM-SOP-106","SM-SOP-109","SM-SOP-552","SM-SOP-184","SM-SOP-511","SM-SOP-513"]:
    found=[it for it in items if (it.get("doc_number") or "")=="MHZYY-JYK-"+N]
    if found:
        print(f"{N}: id={found[0]['id']} title={found[0]['title']!r}")
    else:
        print(f"{N}: 未找到")
