import urllib.request, urllib.parse, json

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
API = BASE + "/api/v1"
USER, PASS = "jinzizheng", "Jzz6827556"


def req(method, url, data=None, headers=None):
    headers = dict(headers or {})
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa
        return -1, repr(e)


print("== build mark ==")
st, body = req("GET", API + "/_diag/build")
print(st, body)

print("== login ==")
st, body = req("POST", API + "/auth/login", {"username": USER, "password": PASS})
tok = json.loads(body).get("access_token")
H = {"Authorization": f"Bearer {tok}"}

print("== plans + preview marker check ==")
st, body = req("GET", API + "/comparison/plans", headers=H)
plans = json.loads(body).get("items", [])
any_marker = False
for p in plans:
    pid = p["id"]
    st, body = req("GET", f"{API}/comparison/plans/{pid}/report/preview", headers=H)
    marker = "（绝对偏倚）" in body
    any_marker = any_marker or marker
    print(f"plan {pid} (group {p.get('group_id')}, items={p.get('compared_count')}) preview:{st} has_abs_marker={marker}")
print("ANY_MARKER_PRESENT" if any_marker else "NO_MARKER_FOUND (live data may not have low-value absolute items configured)")
