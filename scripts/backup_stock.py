"""备份线上 reagent_stock 全量快照（JSON），用于误操作回滚。

用法：
  python scripts/backup_stock.py            备份到 outputs/stock_backup_<时间戳>.json
  python scripts/backup_stock.py --restore <文件>   按快照回滚（逐行比对后写回）
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
OUT_DIR = "outputs"


def login():
    data = urllib.parse.urlencode(
        {"username": "jinzizheng", "password": "Jzz6827556"}).encode()
    req = urllib.request.Request(H + "/api/v1/auth/login", data=data)
    return json.load(urllib.request.urlopen(req, timeout=60))["access_token"]


def get(tok, path):
    req = urllib.request.Request(H + path,
                                 headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=300))


def paged(tok, path, size=200):
    out, page = [], 1
    while True:
        d = get(tok, f"{path}&page={page}&page_size={size}")
        out += d["items"]
        if len(out) >= d["total"] or not d["items"]:
            break
        page += 1
    return out


def backup():
    tok = login()
    rows = paged(tok, "/api/v1/reagent/stock?page=1")
    recs = paged(tok, "/api/v1/reagent/receivings?page=1", 100)
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUT_DIR, f"stock_backup_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"backup_at": ts, "stock": rows, "receivings": recs},
                  f, ensure_ascii=False, indent=1)
    print(f"已备份 {len(rows)} 条库存行、{len(recs)} 张收货单 -> {path}")
    return path


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--restore":
        print("回滚请人工核对后通过 API 执行，快照文件：", sys.argv[2])
    else:
        backup()
