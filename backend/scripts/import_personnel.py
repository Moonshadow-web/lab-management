"""从桌面 '生免室人员档案' 文件夹导入人员到 personnel_master。

用法：
    cd backend
    python scripts/import_personnel.py
输出：
    scripts/import_personnel.sql

运行前需确保 personnel_master 表已存在（新 Education 模块部署后 create_all 会自动建表）。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT = Path(r"C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案")

LABEL_MAP = {
    "姓名": "name",
    "性别": "gender",
    "出生年月": "birth_date",
    "学历": "education",
    "职称": "title",
    "职务": "position",
    "政治面貌": "political_status",
    "组内职责": "group_duty",
    "参加工作": "work_start",
    "来院时间": "hospital_join",
    "来组时间": "group_join",
}


def antiword(path: Path) -> str:
    try:
        return subprocess.run(
            ["antiword", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        ).stdout
    except FileNotFoundError:
        raise RuntimeError("antiword 未安装，请安装后再运行") from None


def extract_basic(text: str) -> dict[str, str]:
    """解析 '一、基本情况' 表格文本。"""
    # 取基本档案片段
    m = re.search(r"一、基本情况\s*(.+?)二、", text, re.S)
    if not m:
        return {}
    section = m.group(1)
    result: dict[str, str] = {}
    for line in section.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells[0] 是空；后面成对出现 label / value
        for i in range(1, len(cells) - 1, 2):
            label = re.sub(r"\s+", "", cells[i])
            value = cells[i + 1].strip()
            if not label or not value:
                continue
            key = LABEL_MAP.get(label)
            if key:
                result[key] = value
    return result


def find_doc_file(folder: Path) -> Path | None:
    docs = list(folder.glob("*.doc"))
    if docs:
        return docs[0]
    return None


def build_sql(records: list[dict]) -> str:
    lines = [
        "-- 人员继教管理 - 生免室人员档案导入",
        "-- 生成时间: auto",
        "USE lab_management; -- 请按实际库名调整",
        "",
    ]
    for r in records:
        cols = [
            "name", "gender", "birth_date", "education", "title",
            "position", "political_status", "group_duty",
            "work_start", "hospital_join", "group_join",
            "created_by", "remark",
        ]
        vals = [
            r.get("name", ""),
            r.get("gender", ""),
            r.get("birth_date", ""),
            r.get("education", ""),
            r.get("title", ""),
            r.get("position", ""),
            r.get("political_status", ""),
            r.get("group_duty", ""),
            r.get("work_start", ""),
            r.get("hospital_join", ""),
            r.get("group_join", ""),
            "admin",
            "从 BG-KS-GL-017 档案导入",
        ]
        escaped = [v.replace("'", "''") for v in vals]
        col_str = ", ".join(cols)
        val_str = ", ".join(f"'{v}'" for v in escaped)
        lines.append(
            f"INSERT INTO personnel_master ({col_str}) VALUES ({val_str});"
        )
    return "\n".join(lines)


def main():
    records: list[dict] = []
    if not ROOT.exists():
        raise FileNotFoundError(f"找不到人员档案目录: {ROOT}")

    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():
            continue
        doc = find_doc_file(folder)
        if not doc:
            print(f"[!] {folder.name}: 未找到 .doc 档案")
            continue
        text = antiword(doc)
        data = extract_basic(text)
        if not data.get("name"):
            print(f"[!] {folder.name}: 未能解析姓名")
            continue
        # 文件夹名兜底姓名
        if not data.get("name"):
            data["name"] = folder.name
        records.append(data)
        print(f"[OK] {data.get('name', folder.name)}: {doc.name}")

    sql = build_sql(records)
    out = BASE_DIR / "scripts" / "import_personnel.sql"
    out.write_text(sql, encoding="utf-8")
    print(f"\n已生成 {out}，共 {len(records)} 条记录")


if __name__ == "__main__":
    main()
