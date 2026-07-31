"""Word (.docx) 辅助工具：接受所有修订、更新首页表头元数据。

用于 ISO15189 文件评审的「接收生成新版本」环节：管理员确认后，后端把成员
上传的修订 docx 一键接受修订、并把版本号/修订号/审核日期/审核人/批准日期/
实施日期写回文档首页表头，再作为正式新版本落盘/COS。
"""
from __future__ import annotations

import io
import zipfile
from typing import Optional

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _tag(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def _remove_namespace_prefix(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def accept_all_track_changes(content: bytes) -> bytes:
    """接受 docx 中所有修订（track changes）：保留插入内容、删除删除内容。"""
    in_buf = io.BytesIO(content)
    out_buf = io.BytesIO()
    revision_rels: set[str] = set()

    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(
        out_buf, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        # 先扫描 document.xml.rels，记录指向 revisions.xml 的 relId
        try:
            rels_data = zin.read("word/_rels/document.xml.rels")
            rels_root = etree.fromstring(rels_data)
            for el in rels_root:
                target = el.get("Target", "")
                if "revision" in target.lower():
                    rid = el.get("Id")
                    if rid:
                        revision_rels.add(rid)
        except KeyError:
            pass

        for item in zin.infolist():
            data = zin.read(item.filename)
            skip = False

            if item.filename == "word/document.xml":
                root = etree.fromstring(data)
                # 1) 删除 <w:del> / <w:moveFrom> 元素（含内容的整段删除）
                for tag in ("del", "moveFrom"):
                    for el in list(root.iter(_tag(tag))):
                        parent = el.getparent()
                        if parent is not None:
                            parent.remove(el)
                # 2) 展开 <w:ins> / <w:moveTo> 元素（保留子节点，移除外包标签）
                for tag in ("ins", "moveTo"):
                    for el in list(root.iter(_tag(tag))):
                        parent = el.getparent()
                        if parent is None:
                            continue
                        idx = list(parent).index(el)
                        for child in list(el):
                            parent.insert(idx, child)
                            idx += 1
                        parent.remove(el)
                # 3) 去掉 rPr 中标记修订属性的 <w:ins/> <w:del/> <w:moveFrom/> <w:moveTo/>
                for rpr in root.iter(_tag("rPr")):
                    for tag in ("ins", "del", "moveFrom", "moveTo"):
                        for el in rpr.findall(_tag(tag)):
                            rpr.remove(el)
                # 4) 去掉各种 range 标记
                for tag in (
                    "customXmlMoveFromRangeStart",
                    "customXmlMoveFromRangeEnd",
                    "customXmlMoveToRangeStart",
                    "customXmlMoveToRangeEnd",
                    "moveFromRangeStart",
                    "moveFromRangeEnd",
                    "moveToRangeStart",
                    "moveToRangeEnd",
                ):
                    for el in list(root.iter(_tag(tag))):
                        parent = el.getparent()
                        if parent is not None:
                            parent.remove(el)
                data = etree.tostring(
                    root, xml_declaration=True, encoding="UTF-8", standalone=True
                )

            elif item.filename == "[Content_Types].xml":
                root = etree.fromstring(data)
                for el in list(root):
                    ct = el.get("ContentType", "")
                    if "revision" in ct.lower():
                        root.remove(el)
                data = etree.tostring(
                    root, xml_declaration=True, encoding="UTF-8", standalone=True
                )

            elif item.filename == "word/_rels/document.xml.rels":
                root = etree.fromstring(data)
                for el in list(root):
                    target = el.get("Target", "")
                    if "revision" in target.lower():
                        root.remove(el)
                data = etree.tostring(
                    root, xml_declaration=True, encoding="UTF-8", standalone=True
                )

            elif "revision" in item.filename.lower():
                skip = True

            if not skip:
                zout.writestr(item, data)

    return out_buf.getvalue()


def update_docx_header_table(content: bytes, updates: dict[str, str]) -> bytes:
    """更新 docx 首页表头表格中的元数据。

    updates 示例：
      {"版本号": "2.0", "修订号": "0", "审核日期": "2026-08-01",
       "审核者": "杨静", "批准日期": "2026-09-01", "实施日期": "2026-09-01"}
    匹配规则：单元格文本含关键词；若该单元格本身为 "关键词：值" 则改写值；
    否则改写同一行下一单元格的值（常见 SOP 表头布局）。
    """
    from docx import Document

    doc = Document(io.BytesIO(content))
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = row.cells
            for i, cell in enumerate(cells):
                txt = cell.text.strip()
                for key, val in updates.items():
                    if key not in txt:
                        continue
                    # 形式一：单元格内为 "关键词：值" / "关键词:值"
                    if any(sep in txt for sep in ("：", ":")) and txt.startswith(key):
                        # 保留原有的冒号风格
                        sep = "：" if "：" in txt else ":"
                        cell.text = key + sep + str(val)
                    # 形式二：关键词在左列，值在右列下一单元格
                    elif i + 1 < len(cells):
                        cells[i + 1].text = str(val)
                    break
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def is_docx(content: bytes) -> bool:
    """通过文件头判断是否为 docx（zip + 含 word/document.xml）。"""
    if len(content) < 4 or content[:4] != b"PK\x03\x04":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as z:
            return "word/document.xml" in z.namelist()
    except Exception:
        return False
