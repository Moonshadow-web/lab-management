"""解析每份 BG-KS-GL-017 档案的各段表格，并把子表记录导入线上库。

支持解析：教育经历 / 工作经历 / 资格证书 / 奖惩 / 继续教育（外出培训进修）。

用法：
    cd backend
    python scripts/import_personnel_full.py            # 预演（不写库，打印将导入的记录）
    python scripts/import_personnel_full.py --commit   # 正式写入线上库

设计要点：
- 每行表格固定 3 列：[时间, 名称/地点, 明细]。新行判定：时间列与名称列都非空；
  否则视为上一行的续行（处理三种换行：日期碎片 "2003.9-2008."+"6"、
  名称换行 "住院医师规范化培"+"训证书"、明细换行 "...优秀"+"奖"）。
- 续行规则：名称列(col1)有内容 → 追加到上一行 col1；时间列(col0)有内容(无名称) →
  追加到上一行时间（日期碎片）；其余追加到 col2。
- "无" 占位行（奖惩/继续教育为空）不会形成新行，且前面无数据行时直接丢弃。
- 写库：先 GET 全量已导入子表记录做幂等去重，避免重复导入；人员主表按姓名映射
  person_id，缺失则顺带补建主表。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DRY_RUN = "--commit" not in sys.argv
ROOT = Path(r"C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案")
HOST = "http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
USERNAME = "jinzizheng"
PASSWORD = "Jzz6827556"

# 中文表头 -> 子表 key
SECTIONS = {
    "教育经历": "education",
    "工作经历": "work_exp",
    "资格证书": "cert",
    "奖惩": "reward",
    "继续教育": "edu_exp",
}

# 子表 key -> 接口路径 + 去重比较字段（不含 person_id）
ENDPOINTS = {
    "education": "/api/v1/education/personnel-education",
    "work_exp": "/api/v1/education/personnel-work-exp",
    "cert": "/api/v1/education/personnel-certs",
    "reward": "/api/v1/education/personnel-rewards",
    "edu_exp": "/api/v1/education/personnel-edu-exp",
}
COMPARE_FIELDS = {
    "education": ["school", "major", "degree", "start_date", "end_date"],
    "work_exp": ["org", "post", "start_date", "end_date"],
    "cert": ["cert_name", "cert_no", "issue_date", "issue_org", "valid_until"],
    "reward": ["reward_type", "title", "date", "org"],
    "edu_exp": ["name", "organizer", "train_date", "hours", "credits", "cert_no"],
}

# 基本情况 -> 字段映射（用于缺失主表时补建）
LABEL_MAP = {
    "姓名": "name", "性别": "gender", "出生年月": "birth_date", "学历": "education",
    "职称": "title", "职务": "position", "政治面貌": "political_status",
    "组内职责": "group_duty", "参加工作": "work_start", "来院时间": "hospital_join",
    "来组时间": "group_join",
}
_DEGREES = ["博士研究生", "博士", "硕士研究生", "硕士", "研究生", "本科", "大专", "中专",
            "高中", "初中", "小学"]


def antiword(path: Path) -> str:
    return subprocess.run(
        ["antiword", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", check=False
    ).stdout


def split_range(s: str) -> tuple[str, str]:
    """把起止时间拆成 (start, end)。

    优先按 '至今' / '至' 作为区间分隔符（如 '2021-09至2024-06'、'1995年至今'），
    再退回 '-'/'~'/'·' 等（如 '2003.9-2008.6'）。'-' 也用于 YYYY-MM 内部，
    故不能先于 '至' 拆分。
    """
    s = (s or "").strip()
    if "至今" in s:
        a = s.split("至今", 1)[0].strip()
        return a, "至今"
    if "至" in s:
        a, b = s.split("至", 1)
        return a.strip(), b.strip()
    for sep in ["-", "~", "—", "～", "·"]:
        if sep in s:
            a, b = s.split(sep, 1)
            return a.strip(), b.strip()
    return s, ""


def extract_degree(text: str) -> str:
    t = (text or "").strip()
    for d in _DEGREES:
        if t.endswith(d):
            return d
    return ""


def _is_fragment(time: str) -> bool:
    """time 是否为“无年份的短碎片”（如 '8' / '.23' / '7'），属于上一行日期的换行。"""
    t = time.strip()
    if not t:
        return False
    if re.search(r"(19|20)\d{2}", t):  # 含 4 位年份 -> 完整日期
        return False
    return len(t) <= 4


def parse_section(text: str, header: str) -> list[list[str]]:
    """返回该 section 的若干行，每行 [time, col1(名称/地点), col2(明细)]。

    续行判定（antiword 单元格超出列宽会换行到下一行）：
    - 名称列(col1)空 -> 续行（时间碎片 '6' 或明细续写 '奖'/'）'）。
    - 名称列非空、时间列空 -> 名称/明细换行（续行）。
    - 名称列与时间列都非空：时间含 4 位年份 -> 新行；时间为无年份短碎片(<=4)
      -> 续行（与上一行日期/名称合并）；否则（如 '2.19.4-至今' 这种异常写法）-> 新行。
    """
    pat = re.escape(header) + r"\s*(.+?)(?=二、|三、|四、|五、|六、|备注)"
    m = re.search(pat, text, re.S)
    if not m:
        return []
    block = m.group(1)
    rows: list[list[str]] = []
    last: list[str] | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if not line.startswith("|"):
            # 无管道换行的续行文本：追加到上一行明细
            if last is not None:
                last[2] = (last[2] + line.strip()).strip()
            continue
        cells = [c.strip() for c in line.split("|")]
        time = cells[1] if len(cells) > 1 else ""
        col1 = cells[2] if len(cells) > 2 else ""
        col2 = cells[3] if len(cells) > 3 else ""
        # 表头行（时间列就是“时间”二字）跳过
        if "时间" in time:
            continue
        if col1.strip() and not time.strip():
            # 名称列有内容、时间列空 -> 上一行名称/明细换行
            if last is not None:
                if col1.strip():
                    last[1] = (last[1] + col1.strip()).strip()
                if col2.strip():
                    last[2] = (last[2] + col2.strip()).strip()
            continue
        if not col1.strip():
            # 名称列空 -> 续行（时间碎片或明细续写）
            if last is not None:
                if time.strip():
                    last[0] = (last[0] + time.strip()).strip()
                if col2.strip():
                    last[2] = (last[2] + col2.strip()).strip()
            continue
        # col1 与时间都非空
        if re.search(r"(19|20)\d{2}", time) or not _is_fragment(time):
            row = [time, col1, col2]
            rows.append(row)
            last = row
        else:
            if last is not None:
                if time.strip():
                    last[0] = (last[0] + time.strip()).strip()
                if col1.strip():
                    last[1] = (last[1] + col1.strip()).strip()
                if col2.strip():
                    last[2] = (last[2] + col2.strip()).strip()
    return [r for r in rows if any(r)]


def parse_all(text: str) -> dict[str, list[list[str]]]:
    out: dict[str, list[list[str]]] = {}
    for header, key in SECTIONS.items():
        out[key] = parse_section(text, header)
    return out


def build_payload(key: str, row: list[str], person_id: int) -> dict:
    """把 [time, col1, col2] 按子表语义映射成接口 payload。"""
    time, col1, col2 = row[0], row[1], row[2]
    if key == "education":
        start, end = split_range(time)
        major = col2
        degree = extract_degree(major)
        if degree:
            major = major[: -len(degree)].strip()
        return {"person_id": person_id, "school": col1, "major": major,
                "degree": degree, "start_date": start, "end_date": end}
    if key == "work_exp":
        start, end = split_range(time)
        return {"person_id": person_id, "org": col1, "post": col2,
                "start_date": start, "end_date": end}
    if key == "cert":
        return {"person_id": person_id, "cert_name": col1, "cert_no": col2,
                "issue_date": time, "issue_org": "", "valid_until": ""}
    if key == "reward":
        return {"person_id": person_id, "date": time, "org": col1, "title": col2,
                "reward_type": "奖励"}
    if key == "edu_exp":
        return {"person_id": person_id, "name": col2, "organizer": col1,
                "train_date": time, "hours": "", "credits": "", "cert_no": ""}
    raise ValueError(key)


# ---------------------------------------------------------------------------
# 线上 API
# ---------------------------------------------------------------------------
def api_call(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{HOST}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", errors="ignore")}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "body": str(e)}


def login() -> str:
    url = f"{HOST}/api/v1/auth/login"
    data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def extract_basic(text: str) -> dict[str, str]:
    m = re.search(r"一、基本情况\s*(.+?)二、", text, re.S)
    if not m:
        return {}
    section = m.group(1)
    result: dict[str, str] = {}
    for line in section.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        for i in range(1, len(cells) - 1, 2):
            label = re.sub(r"\s+", "", cells[i])
            value = cells[i + 1].strip()
            if not label or not value:
                continue
            key = LABEL_MAP.get(label)
            if key:
                result[key] = value
    return result


def get_personnel_map(token: str) -> dict[str, int]:
    res = api_call("GET", "/api/v1/education/personnel?page_size=1000", token=token)
    items = res["body"].get("items", []) if res["status"] == 200 else []
    return {it["name"]: it["id"] for it in items if it.get("name")}


def get_existing(token: str) -> dict[str, set]:
    """拉取 5 张子表全量记录，构建 (person_id, fingerprint) 集合用于幂等去重。"""
    existing: dict[str, set] = {}
    for key, ep in ENDPOINTS.items():
        res = api_call("GET", ep + "?page_size=1000", token=token)
        items = res["body"].get("items", []) if res["status"] == 200 else []
        s: set = set()
        for it in items:
            fp = tuple(str(it.get(f, "")).strip() for f in COMPARE_FIELDS[key])
            s.add((it.get("person_id"), fp))
        existing[key] = s
        if res["status"] != 200:
            print(f"  [warn] 拉取 {key} 现有记录失败 {res['status']}，去重将不可用")
    return existing


def fingerprint(key: str, payload: dict) -> tuple:
    return tuple(str(payload.get(f, "")).strip() for f in COMPARE_FIELDS[key])


def find_doc_file(folder: Path) -> Path | None:
    docs = list(folder.glob("*.doc"))
    return docs[0] if docs else None


def main():
    print(f"模式: {'预演(不写库)' if DRY_RUN else '正式写入'}")

    # 解析所有文件夹
    parsed: dict[str, dict] = {}
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():
            continue
        doc = find_doc_file(folder)
        if not doc:
            print(f"[!] {folder.name}: 无 .doc")
            continue
        text = antiword(doc)
        basic = extract_basic(text)
        name = basic.get("name") or folder.name
        data = parse_all(text)
        parsed[folder.name] = {"name": name, "basic": basic, "data": data}

    # 预演打印
    if DRY_RUN:
        total_all = 0
        for folder_name, info in parsed.items():
            print(f"\n=== {folder_name}  (姓名={info['name']}) ===")
            for key, rows in info["data"].items():
                print(f"  -- {key}: {len(rows)} 条")
                for r in rows:
                    p = build_payload(key, r, 0)
                    print(f"      {p}")
                total_all += len(rows)
        print(f"\n预演完成，共 {total_all} 条子表记录待导入（加 --commit 正式写入）。")
        return

    # 正式写入
    token = login()
    print("登录成功")
    pmap = get_personnel_map(token)
    existing = get_existing(token)

    created_total = 0
    skipped_total = 0
    for folder_name, info in parsed.items():
        name = info["name"]
        pid = pmap.get(name)
        if pid is None:
            # 顺带补建主表
            payload = {k: info["basic"].get(k, "") for k in LABEL_MAP.values()}
            payload["name"] = name
            res = api_call("POST", "/api/v1/education/personnel", payload, token)
            if res["status"] == 201:
                pid = res["body"].get("id")
                pmap[name] = pid
                print(f"[新建主表] {name} -> id={pid}")
            else:
                print(f"[FAIL 主表] {name}: {res['status']} {res['body']}")
                continue
        for key, rows in info["data"].items():
            for r in rows:
                payload = build_payload(key, r, pid)
                fp = fingerprint(key, payload)
                if (pid, fp) in existing[key]:
                    skipped_total += 1
                    continue
                res = api_call("POST", ENDPOINTS[key], payload, token)
                if res["status"] == 201:
                    created_total += 1
                    existing[key].add((pid, fp))
                else:
                    print(f"[FAIL] {name}/{key}: {res['status']} {res['body']}")
    print(f"\n写入完成：新增 {created_total} 条，跳过重复 {skipped_total} 条。")


if __name__ == "__main__":
    main()
