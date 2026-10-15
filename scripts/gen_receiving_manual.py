# -*- coding: utf-8 -*-
"""生成《试剂到货接收模块操作说明书》（试剂配送人员用）docx。"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r"d:\workbuddyprojects\网页版-生免速查工具\试剂到货接收操作说明书.docx"

doc = Document()

# ---- 基础字体（中英文均用微软雅黑，避免中文乱码） ----
style = doc.styles["Normal"]
style.font.name = "微软雅黑"
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

CN = RGBColor(0x1A, 0x36, 0x5D)   # 深蓝主色
SUB = RGBColor(0x60, 0x60, 0x60)  # 灰色副文

def set_cn(run):
    run.font.name = "微软雅黑"
    r = run._element
    r.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

def heading(text, level=1):
    p = doc.add_heading("", level=level)
    run = p.add_run(text)
    set_cn(run)
    if level == 1:
        run.font.color.rgb = CN
        run.font.size = Pt(15)
    else:
        run.font.color.rgb = CN
        run.font.size = Pt(12.5)
    return p

def para(text, size=10.5, bold=False, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_cn(run)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    if align:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p

def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        set_cn(r1); r1.bold = True; r1.font.size = Pt(10.5)
        r2 = p.add_run(text)
        set_cn(r2); r2.font.size = Pt(10.5)
    else:
        r = p.add_run(text)
        set_cn(r); r.font.size = Pt(10.5)
    return p

def numbered(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Number")
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        set_cn(r1); r1.bold = True; r1.font.size = Pt(10.5)
    r2 = p.add_run(text)
    set_cn(r2); r2.font.size = Pt(10.5)
    return p

def add_table(headers, rows, col_widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(h)
        set_cn(run); run.bold = True; run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        # 表头底色
        tcPr = hdr[i]._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "1A365D")
        tcPr.append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            set_cn(run); run.font.size = Pt(9.5)
    if col_widths:
        for i, w in enumerate(col_widths):
            for r in t.rows:
                r.cells[i].width = Inches(w)
    return t

def callout(title, text):
    """提示框样式的段落（底色浅蓝）。"""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "EAF1FB")
    pPr.append(shd)
    r1 = p.add_run("【" + title + "】")
    set_cn(r1); r1.bold = True; r1.font.size = Pt(10.5); r1.font.color.rgb = CN
    r2 = p.add_run(text)
    set_cn(r2); r2.font.size = Pt(10.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    return p

# ====================== 封面 ======================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("试剂到货接收模块")
set_cn(r); r.bold = True; r.font.size = Pt(26); r.font.color.rgb = CN
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("—— 试剂配送人员操作说明书 ——")
set_cn(r); r.font.size = Pt(14); r.font.color.rgb = SUB
doc.add_paragraph()
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = meta.add_run("民 航 总 医 院 检 验 科 · 生 化 免 疫 组\n检验科综合管理系统（Web 版）")
set_cn(r); r.font.size = Pt(11); r.font.color.rgb = SUB
doc.add_paragraph()
ver = doc.add_paragraph()
ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = ver.add_run("适用角色：试剂配送（reagent_delivery）　|　版本：V1.0")
set_cn(r); r.font.size = Pt(10); r.font.color.rgb = SUB

doc.add_page_break()

# ====================== 一、概述 ======================
heading("一、模块概述", 1)
para("「到货接收」用于登记供应商配送到科的试剂/校准品，确认接收后系统自动更新实时库存。"
     "本模块是试剂配送人员的专属工作台——登录后整个系统仅显示本页面，界面简洁、操作聚焦。", space_after=8)
callout("你能做什么", "新建到货接收单 → 添加试剂明细 → 确认接收（试剂自动入库）→ 打印签字联。"
        "你只能查看和编辑自己创建的、尚未确认的单据，不能删除，也不能进入其他任何模块。")

# ====================== 二、登录 ======================
heading("二、登录与界面", 1)
numbered("打开系统网址，使用管理员分配给你的账号登录（用户名通常为你的姓名拼音，如 shijipeisong）。", "登录：")
numbered("登录后系统会自动跳转到「到货接收」页面——你不会看到「工作台」「试剂管理」等其他菜单。", "落地页：")
numbered("页面顶部有「生化凝血 / 免疫」责任库切换标签，按你本次收货所属专业组选择；中部是收货单列表，右上角为「新建收货单」按钮。", "页面构成：")
callout("看不到其他模块属正常", "试剂配送是受限账户，登录后只能使用「到货接收」一个功能，看不到库存、目录、盘库、订购等管理页面，这是权限设计使然，并非故障。")

# ====================== 三、新建收货单 ======================
heading("三、新建一张到货接收单", 1)
para("点击右上角「新建收货单」，弹出录入窗口，按以下顺序填写：", space_after=6)

heading("3.1 单头信息", 2)
add_table(
    ["字段", "是否必填", "说明"],
    [
        ["收货单号", "必填", "系统自动生成（如 RCV-2026-08-001），一般无需修改；留空会提示必填"],
        ["日期", "选填", "默认当天，可改"],
        ["送货人", "选填", "填写供应商送货人姓名"],
        ["接收人", "选填", "默认填写为当前登录人，可核对/修改"],
        ["备注", "选填", "如物流单号、特殊情况说明等"],
    ],
    col_widths=[1.4, 1.0, 4.0],
)
doc.add_paragraph()

heading("3.2 添加试剂明细（至少 1 行）", 2)
para("逐行登记本次到货的试剂。每行包含：试剂（下拉选择）、批号、效期、数量。两种添加方式：", space_after=6)
bullet("在明细表格的「试剂」列下拉框中直接选择（列出全部试剂目录）。", "方式一：")
bullet("用窗口顶部的「搜索添加试剂」框，输入名称/品牌/编码模糊搜索，点选即加入明细。", "方式二：")
callout("数量至少为 1", "「数量」列最小值为 1；批号、效期按实物如实填写。点击行尾的删除按钮可移除该行。")

heading("3.3 保存", 2)
numbered("确认明细行数 ≥ 1 且收货单号已填，点击「提交」。", "提交：")
numbered("保存成功后单据状态为「待确认」，此时试剂尚未进入库存——需要进一步「确认接收」才会入库。", "状态：")
callout("保存 ≠ 入库", "新建并保存后，试剂不会立刻进入实时库存，列表状态显示「待确认」。只有执行下一步「确认接收」后，库存才会更新。")

# ====================== 四、确认接收 ======================
heading("四、确认接收（试剂入库）", 1)
numbered("在收货单列表中找到目标单据，点击操作列的「确认接收」。", "入口：")
numbered("系统弹出二次确认：「确认接收？确认后试剂将进入实时库存。」点击确定。", "二次确认：")
numbered("提示「已确认接收，库存已更新」，列表状态变为「已确认」，并显示确认人与确认时间。", "结果：")
para("此后系统按「试剂 + 批号」匹配库存：已有同批号记录则累加数量，没有则新建一条库存记录。", space_after=6)
callout("已确认不可再改", "单据一旦确认接收，便不能再编辑（避免与已入库库存脱节）；如确认有误，需联系管理员（admin）处理。重复点击确认会提示「已确认，无需重复确认」，不会重复加库存。")

# ====================== 五、查看/编辑/打印 ======================
heading("五、查看、编辑与打印", 1)
add_table(
    ["操作", "条件 / 说明"],
    [
        ["详情", "点击「详情」查看单号、状态及全部试剂明细"],
        ["编辑", "仅可编辑自己创建、且「待确认」的单；已确认或他人单据不可编辑"],
        ["打印", "点击「打印」弹出《试剂到货接收单》预览，可打印带签字栏的纸质联，用于科室留存"],
    ],
    col_widths=[1.2, 5.2],
)
doc.add_paragraph()
callout("只能看自己的单", "列表中你只能看到自己创建的收货单；管理员和试剂管理员可以看到全部单据。如果你看不到某张单，说明它不是你创建的。")

# ====================== 六、注意事项 ======================
heading("六、权限与注意事项", 1)
bullet("只能新建、确认、编辑自己创建的未确认收货单。", "权限范围：")
bullet("没有删除按钮，也不能删除任何收货单（删除仅限管理员）。", "不可删除：")
bullet("确认接收后单据锁定，不能修改；如需更正请联系管理员。", "确认即锁定：")
bullet("保存后务必记得点「确认接收」，否则试剂不会进入库存，临床将无试剂可用。", "关键动作：")
bullet("批号、效期务必如实填写，关系到效期预警与质量追溯。", "数据准确：")
bullet("登录后看不到「工作台」「试剂管理」等菜单属正常权限设计。", "界面简洁：")

# ====================== 七、常见问题 ======================
heading("七、常见问题（FAQ）", 1)
faqs = [
    ("为什么我看不到库存/目录/盘库等页面？", "试剂配送是受限账户，登录后仅开放「到货接收」一个功能，看不到其他管理模块属正常设计。"),
    ("保存后为什么库存没变？", "保存只是登记，状态为「待确认」；需再点「确认接收」才会写入实时库存。"),
    ("确认错了能改吗？", "不能。已确认单据锁定，请联系管理员处理。"),
    ("我能删掉一张填错的单吗？", "不能。删除功能仅管理员可用；未确认的单可以点「编辑」修改内容。"),
    ("为什么列表里找不到别人建的收货单？", "你只能查看自己创建的收货单，这是权限限制，并非数据丢失。"),
    ("收货单号能自己编吗？", "系统自动生成，一般无需修改；如留空提交会提示必填。"),
]
for q, a in faqs:
    p = doc.add_paragraph()
    r = p.add_run("Q：" + q)
    set_cn(r); r.bold = True; r.font.size = Pt(10.5); r.font.color.rgb = CN
    p.paragraph_format.space_after = Pt(2)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("A：" + a)
    set_cn(r2); r2.font.size = Pt(10.5)
    p2.paragraph_format.space_after = Pt(8)

doc.add_paragraph()
foot = doc.add_paragraph()
foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = foot.add_run("—— 本说明书依据检验科综合管理系统「到货接收」模块实际功能编写，如有流程调整以系统为准 ——")
set_cn(r); r.font.size = Pt(9); r.font.color.rgb = SUB

doc.save(OUT)
print("saved:", OUT)
