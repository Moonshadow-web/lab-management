"""生成「试剂订购表」打印预览 HTML（含受控表格页脚），用于确认页脚排版。

用法：python scripts/gen_order_print_preview.py [order_id]
"""
import json
import sys
import urllib.parse
import urllib.request

H = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
OUT = "outputs/试剂订购表_打印预览.html"
FOOT = "表格编号：BG-SM-CZ-036　　民航总医院检验科生化免疫组　　生效日期：2026.9.1"


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


CSS = """
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#1f2937;padding:24px}
h2{font-size:18px;margin:0 0 4px}
.meta{color:#6b7280;font-size:13px;margin-bottom:16px}
table{border-collapse:collapse;width:100%;margin-bottom:8px;font-size:13px}
th,td{border:1px solid #cbd5e1;padding:6px 8px;text-align:left}
th{background:#f1f5f9;font-weight:600}
.num{text-align:center}
table.doc{border:0;margin:0}
table.doc > * > tr > td{border:0;padding:0}
.doc-foot{font-size:12px;color:#374151;padding-top:10px}
@media print{body{padding:8px}thead{display:table-header-group}tfoot{display:table-footer-group}}
"""


def main():
    oid = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tok = login()
    items = {i["id"]: i for i in paged(tok, "/api/v1/reagent/items?page=1")}
    orders = paged(tok, "/api/v1/reagent/orders?page=1", 100)
    o = [x for x in orders if x["id"] == oid][0]

    rows = ""
    for it in o["items"][:12]:
        m = items.get(it["item_id"], {})
        rows += (
            "<tr><td>" + str(m.get("material_code", "")) + "</td><td>"
            + str(m.get("name", it["item_id"])) + "</td><td>"
            + str(m.get("spec", "")) + "</td><td>"
            + str(m.get("unit", "")) + "</td><td class='num'>"
            + str(it["ordered_quantity"]) + "</td></tr>")

    body = ("<table><thead><tr><th>材料编码</th><th>名称</th><th>规格</th>"
            "<th>单位</th><th class='num'>订购数量</th></tr><tbody>"
            + rows + "</tbody></table>")

    doc = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>试剂订购表（打印预览）</title><style>" + CSS + "</style></head><body>"
        "<table class='doc'>"
        "<thead><tr><td><h2>试剂订购表</h2>"
        "<div class='meta'>订单号：" + str(o["order_no"]) + "　日期："
        + str(o["order_date"]) + "　责任库：" + str(o.get("library", ""))
        + "　类型：" + str(o.get("order_type", "")) + "</div></td></tr></thead>"
        "<tbody><tr><td>" + body + "</td></tr></tbody>"
        "<tfoot><tr><td><div class='doc-foot'>" + FOOT + "</div></td></tr></tfoot>"
        "</table></body></html>")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"已生成 {OUT}（示例 {min(12, len(o['items']))} 行 + 页脚）")


if __name__ == "__main__":
    main()
