"""复刻 eqa.py _lookup_units 验证胶体金对应是否生效，且不影响标准血清学。"""
import sqlite3, re

DB = r"d:\workbuddyprojects\网页版-生免速查工具\data\app.db"
c = sqlite3.connect(DB)


def _norm_item(s):
    s = (s or "").strip()
    s = s.replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "")
    return s.lower()


rows = c.execute("SELECT name, aliases, unit FROM test_items").fetchall()
index = []
for name, aliases, unit in rows:
    keys = {_norm_item(name)}
    for a in (aliases or "").split(","):
        a = a.strip()
        if a:
            keys.add(_norm_item(a))
    index.append((keys, unit or ""))


def lookup(names):
    out = {}
    for n in names:
        nn = _norm_item(n)
        unit = ""
        if nn:
            for keys, u in index:
                if nn in keys:
                    unit = u
                    break
            if not unit:
                for keys, u in index:
                    for k in keys:
                        if k and len(k) >= 2 and len(nn) >= 2 and (k in nn or nn in k):
                            unit = u
                            break
                    if unit:
                        break
        out[n] = unit
    return out


def split(raw):
    raw = re.sub(r"^(具体项目|项目|检测项目)[：:]\s*", "", raw or "")
    return [p.strip() for p in re.split(r"[、,，/]", raw) if p.strip()]


print("=== 快速检测计划（应全部 = 定性）===")
for item in ["HIV（胶体金）、HBsAg（胶体金）、TP（胶体金）、HCV（胶体金）"]:
    res = lookup(split(item))
    for k, v in res.items():
        flag = "OK定性" if "定性" in v else "!!非定性:" + v
        print(f"  {k:20s} -> {v:20s} [{flag}]")

print("\n=== 标准血清学(系列A/B/C)（应保持 COI/S·CO 等，不被定性覆盖）===")
for item in ["HBsAg、HBsAb、HBeAg、HBeAb、HBcAb、HCVAb",
             "HIV、TPAb、TRUST",
             "HIV、梅毒特异性抗体"]:
    res = lookup(split(item))
    for k, v in res.items():
        print(f"  {k:20s} -> {v}")
c.close()
