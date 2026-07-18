"""仅查询：打印 live 的 interlab plans 与 instruments，便于确认导入目标与机器 id 映射。"""
import json, urllib.request, urllib.parse

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"

def api(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def main():
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=urllib.parse.urlencode({"username": "jinzizheng", "password": "Jzz6827556"}).encode(),
        method="POST")).read())["access_token"]

    plans = api("GET", "/api/v1/interlab/plans", tok)
    print("==== PLANS ====")
    print(json.dumps(plans, ensure_ascii=False, indent=2))

    insts = api("GET", "/api/v1/interlab/instruments", tok)
    print("\n==== INSTRUMENTS (id -> name/model) ====")
    for i in insts:
        print(i["id"], "|", i.get("name"), "|", i.get("model"), "|", i.get("status"))

if __name__ == "__main__":
    main()
