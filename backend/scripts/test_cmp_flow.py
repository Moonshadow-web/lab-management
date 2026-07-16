"""全流程：新建计划→录入(含遮蔽项目)→预览(校验遮蔽渲染)→生成docx→删除计划清理。"""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8123/api/v1"


def _req(method, path, token=None, data=None, form=None):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    _, d = _req("POST", "/auth/login",
                form={"username": "jinzizheng", "password": "Jzz6827556"})
    tok = d["access_token"]
    print("login OK")

    # 取生化分组
    _, groups = _req("GET", "/comparison/groups", token=tok)
    g = next(x for x in groups if x["name"] == "生化分析仪")
    gid = g["id"]
    ids = g["instrument_ids"]
    ref = g["reference_instrument_id"]
    compared = [i for i in ids if i != ref]
    print(f"group={gid} ids={ids} ref={ref} compared={compared} items={len(g['items'])}")

    # 人为把第1个项目设为只适用参照+第一台比对仪（制造遮蔽：其余比对仪被遮蔽）
    items = [dict(it) for it in g["items"]]
    mask_item = items[0]["name"]
    if compared:
        items[0]["instrument_ids"] = [ref, compared[0]]  # 仅这两台适用
    st, _ = _req("PUT", f"/comparison/groups/{gid}", token=tok, data={"items": items})
    print("set masking on item", mask_item, "-> only", items[0]["instrument_ids"], "status", st)

    # 新建计划
    st, p = _req("POST", "/comparison/plans", token=tok,
                 data={"group_id": gid, "year": 2026, "half": 1,
                       "form_code": g["form_code"], "compared_at": "2026-06-30",
                       "operator": "测试", "reviewer": "复核"})
    pid = p["id"]
    print("plan created", pid, "status", st)

    # 录入水平1：给所有比对仪填值（遮蔽仪也故意填，验证保存时被过滤/预览遮蔽）
    quant = []
    for cid in compared:
        pass
    quant.append({
        "item": mask_item, "level": 1, "reference_value": "10.0",
        "values": {str(c): "10.1" for c in compared},
    })
    # 第2个项目正常（全部适用）
    if len(items) > 1:
        quant.append({
            "item": items[1]["name"], "level": 1, "reference_value": "5.0",
            "values": {str(c): "5.05" for c in compared},
        })
    st, _ = _req("PUT", f"/comparison/plans/{pid}/results", token=tok,
                 data={"quant": quant, "qual": []})
    print("results saved status", st)

    # 预览：检查遮蔽项目行是否出现 mask 单元格
    st, prev = _req("GET", f"/comparison/plans/{pid}/report/preview", token=tok)
    html = prev.get("html", "")
    masked_cnt = html.count('class="mask"')
    print("preview status", st, "masked-cells in html =", masked_cnt)

    # 生成 docx
    st, pp = _req("POST", f"/comparison/plans/{pid}/report/generate", token=tok)
    print("generate docx status", st, "file=", pp.get("report_filename"))

    # 清理：删除计划 + 还原项目遮蔽
    _req("DELETE", f"/comparison/plans/{pid}", token=tok)
    items[0].pop("instrument_ids", None)
    items[0]["instrument_ids"] = []
    _req("PUT", f"/comparison/groups/{gid}", token=tok, data={"items": items})
    print("cleanup done (plan deleted, masking reset)")

    print("\nRESULT:",
          "PASS" if (masked_cnt > 0 and st == 200) else "CHECK",
          "- 遮蔽单元格数应>0 且报告生成成功")


if __name__ == "__main__":
    main()
