"""核对线上尿液 docx 修复后的月结行：单位 + 质量目标。"""
import urllib.request, urllib.parse, json

BASE = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1"
USER, PWD = "jinzizheng", "Jzz6827556"


def _req(method, path, token=None):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token} if token else {}, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    st, body = _req("POST", "/auth/login", )
    # login needs form
    import urllib.parse as up
    req = urllib.request.Request(BASE + "/auth/login",
        data=up.urlencode({"username": USER, "password": PWD}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    r = urllib.request.urlopen(req, timeout=40)
    token = json.loads(r.read().decode())["access_token"]

    items = ["磷", "总钙", "尿磷", "尿钙", "尿尿素", "尿肌酐", "尿镁", "镁", "尿钾", "尿钠"]
    for it in items:
        st, body = _req("GET", f"/qc-summaries?test_item={urllib.parse.quote(it)}&page_size=50", token)
        if not isinstance(body, dict):
            print(f"{it}: ERR {st} {body}")
            continue
        rows = body.get("items", [])
        if not rows:
            print(f"{it}: (no qc rows)")
            continue
        for s in rows[:6]:
            print(f"  {it:6s} lv={s.get('level'):4s} inst={s.get('instrument'):12s} unit={s.get('unit'):8s} goal={s.get('quality_goal')}")


if __name__ == "__main__":
    main()
