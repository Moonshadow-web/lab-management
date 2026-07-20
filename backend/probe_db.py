import pymysql, traceback
cfg = dict(host="10.0.1.18", port=3306, user="labapp", password="Jzz6827556",
           database="cloud1-0gjhamv53ff2298d", connect_timeout=8)
try:
    c = pymysql.connect(**cfg)
    cur = c.cursor()
    cur.execute("SELECT username, role, roles FROM users ORDER BY id")
    print("== users ==")
    for r in cur.fetchall():
        print(r)
    cur.execute("SELECT module_key, role_code FROM module_permissions ORDER BY module_key, role_code")
    print("== module_permissions ==")
    for r in cur.fetchall():
        print(r)
    c.close()
except Exception:
    traceback.print_exc()
