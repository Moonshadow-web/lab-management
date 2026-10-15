# -*- coding: utf-8 -*-
"""生成件③软著《补正情况说明》docx —— 供作为「其他相关证明文件」上传。"""
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = os.path.join(os.path.dirname(__file__), "件3_补正情况说明.docx")

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def set_cn(run, font="宋体", size=12, bold=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)


def para(text, size=12, bold=False, indent=2, align=None, space_after=6):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * indent)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.5
    if align:
        p.alignment = align
    set_cn(p.add_run(text), size=size, bold=bold)
    return p


# 标题
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_cn(t.add_run("补正情况说明"), "黑体", 18, bold=True)

doc.add_paragraph()

para("中国版权保护中心：", indent=0)
para("贵中心于 2026 年 9 月 7 日发出的《软件著作权登记申请补正通知书》"
     "（流水号：2026R11L2658452）已收悉。现就通知书所列事项逐一说明并补正如下。", indent=2)

# 基本信息
para("一、申请基本信息", bold=True, indent=2)
para("软件全称：检验科生化免疫组室内质控与靶值管理软件", indent=2)
para("软件简称：室内质控与靶值管理软件", indent=2)
para("版本号：V1.0", indent=2)
para("著作权人：金子铮（自然人）", indent=2)

# 第一条
para("二、关于「申请确认签章页」的补正", bold=True, indent=2)
para("已按通知书要求，在登记系统中在线生成申请确认签章页并使用 A4 纸打印，"
     "由申请人本人亲笔签名并签署日期，扫描为 PDF 格式文件后上传至申请确认签章页栏目。"
     "本次签章为自然人亲笔签名，不涉及印章，故无需另行提交辅助照片证明。", indent=2)

# 第二条
para("三、关于「鉴别材料内容与软件名称所体现的功能或性能不相符或不完整」的补正", bold=True, indent=2)
para("经核实，该项系文档鉴别材料（软件说明书）内容过薄所致。原提交的说明书共 9 页、"
     "正文约 2600 字，未能充分、完整地说明软件名称中「室内质控」与「靶值管理」"
     "两项核心功能的具体实现，故被认定为内容不完整。现已重新编制说明书，"
     "调整后共 17 页、正文约 1 万字、附界面截图 7 张，主要补充内容如下：", indent=2)

items = [
    "1. 第 2 页新增 1.1「软件名称与功能的对应关系」：以表格形式将软件名称中"
    "「室内质控」「靶值管理」两项核心要素逐条对应到软件的具体功能模块及本说明书对应章节，"
    "便于核对软件功能与软件名称的一致性。",
    "2. 第 3 至 10 页扩充第三章软件功能模块：3.1 质控数据录入与管理（第 3 页）、"
    "3.2 Westgard 多规则判定引擎（第 4 页）、3.3 多源规则冲突消解（第 5 页）、"
    "3.4 累计靶值管理（第 5 至 6 页，含建批、即刻法 SI 界值判定、常规法、"
    "按分析物分别累计、失控值保留、靶值确立与存档、重算调整共七项功能）、"
    "3.5 质控物管理（第 7 页）、3.6 质控月结与总结报告（第 7 至 9 页）、"
    "3.7 质控图与文件存档（第 10 页）、3.8 权限控制（第 10 页），"
    "各节均附真实软件界面截图予以佐证。",
    "3. 第 11 至 13 页新增第五章「主要数据结构」：列明质控记录表、质控月结汇总表、"
    "质控日值明细表、月小结文字报告表、质控品表、批号靶值主表与测定明细表共 7 张数据表"
    "的字段名称、类型与含义。",
    "4. 第 13 至 14 页新增第六章「软件接口清单」：列明质控记录、月结与报告、"
    "靶值管理、质控品共 4 组 30 个接口的名称、请求方式与功能说明。",
    "5. 第 15 至 16 页新增第八章「术语与缩略语说明」：对室内质控、Westgard 多规则、"
    "各判定规则、即刻法、常规法、SI 界值表、CV%、在控率、质量目标、ISO 15189 等术语"
    "逐一释义。",
    "6. 第 17 页新增「附录 界面截图索引」：以表格形式标明所附 7 张界面截图各自"
    "展示的软件功能及对应章节，用于佐证软件功能与软件名称相符。",
    "7. 说明书每页页眉均标注「检验科生化免疫组室内质控与靶值管理软件 V1.0」及页码，"
    "确保鉴别材料与申请表中软件全称、版本号完全一致。",
]
for it in items:
    para(it, indent=2)

para("四、关于程序鉴别材料（源程序）的说明", bold=True, indent=2)
para("原提交的源程序共 60 页，为前后各连续 30 页的规范交存，"
     "页眉标注软件全称与版本号，内容涵盖质控数据管理、Westgard 多规则判定、"
     "累计靶值、月结报告等模块（全文「质控」出现 123 次、「靶值」出现 88 次、"
     "「质控品」出现 51 次），与软件名称所体现的功能相符。"
     "因原导出文件末页存在一页空白，实际为 61 页，与页眉所标「共 60 页」不一致，"
     "现已删除该空白页，修正后为 60 页，其余 60 页内容未作任何改动。", indent=2)

para("五、其他说明", bold=True, indent=2)
para("本次补正仅对文档鉴别材料（说明书）作补充完善，并对程序鉴别材料的空白页作删除处理，"
     "软件名称、版本号、著作权人、开发完成日期等申请信息均无变更。"
     "以上补正材料已随本说明一并提交，请予以审核。", indent=2)

doc.add_paragraph()
para("说明人：金子铮", indent=0, align=WD_ALIGN_PARAGRAPH.RIGHT)
para("2026 年 9 月 7 日", indent=0, align=WD_ALIGN_PARAGRAPH.RIGHT)

doc.save(OUT)
print("saved:", OUT)
