# -*- coding: utf-8 -*-
"""生成件②《检验科生化免疫组室间质评与比对管理软件》软件说明书(用户手册) Word 文档。
含运行环境、功能模块详述、操作流程、4 个界面截图占位框，版面可满足软著≥15页要求。
著作权人按件①实际申报名义统一为：金子铮（个人）。
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = os.path.join(os.path.dirname(__file__), "件2_说明书.docx")

doc = Document()

# 默认字体（含中文）
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(11)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

def set_cn(run, font="宋体", size=11, bold=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    r = run._element
    r.rPr.rFonts.set(qn("w:eastAsia"), font)

def heading(text, level=1):
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    set_cn(run, "黑体", 14 if level == 1 else 12, bold=True)
    return p

def para(text, size=11, bold=False, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    set_cn(run, "宋体", size, bold)
    return p

def placeholder(caption):
    """灰色截图占位框"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run("【截图占位 — " + caption + "】\n（请在此处粘贴该界面截图，并删除本行提示文字）")
    set_cn(run, "宋体", 10, bold=True)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    pPr = p._p.get_or_add_pPr()
    shd = pPr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "F2F2F2"})
    pPr.append(shd)
    return p

# ===== 封面 =====
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("检验科生化免疫组\n室间质评与比对管理软件\n软件说明书（用户手册）")
set_cn(r, "黑体", 20, bold=True)

doc.add_paragraph()
info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = info.add_run("软件全称：检验科生化免疫组室间质评与比对管理软件\n"
                 "软件简称：质评比对管理软件\n"
                 "版本号：V1.0\n"
                 "著作权人：金子铮\n"
                 "开发完成日期：2026-06-30\n"
                 "开发方式：独立开发")
set_cn(r, "宋体", 12)

doc.add_page_break()

# ===== 1 软件概述 =====
heading("1 软件概述", 1)
para("检验科生化免疫组室间质评与比对管理软件（简称：质评比对管理软件）是面向医院检验科"
     "生化免疫专业组开发的实验室信息管理系统子系统，用于统一管理室间质评（EQA）、仪器间比对、"
     "室间比对以及多源质量目标，支撑 ISO 15189 医学实验室质量和能力认可对检验质量管理的受控要求。")
para("本软件采用 B/S（浏览器/服务器）架构，用户通过浏览器即可访问，无需安装客户端。"
     "系统对室间质评成绩、仪器间偏倚、室间符合率及允许总误差质量目标进行统一采集、计算、判定与归档，"
     "实现检验比对与质评工作的信息化、规范化、可追溯管理。")

# ===== 2 运行环境 =====
heading("2 运行环境", 1)
para("（一）硬件环境")
para("开发的硬件环境：通用 PC（Intel i5 / 16GB 内存 / 512GB SSD）。", indent=True)
para("运行的硬件环境：云服务器（2 核 4GB 内存 / 100GB SSD）。", indent=True)
para("（二）软件环境")
para("开发该软件的操作系统：Windows 10 / 11。", indent=True)
para("软件开发环境 / 开发工具：Python 3.13、VS Code、Node.js 22、Git。", indent=True)
para("该软件的运行平台 / 操作系统：Linux + Chrome / Edge 浏览器。", indent=True)
para("软件运行支撑环境 / 支持软件：MySQL 8.0（TDSQL-C）、Nginx、uvicorn（ASGI）、"
     "Python 3.13 运行时、腾讯云 CloudBase 容器平台。", indent=True)

# ===== 3 软件功能模块 =====
heading("3 软件功能模块", 1)

heading("3.1 室间质评计划管理", 2)
para("室间质评计划管理模块维护各专业组参与的室间质评计划与成绩，主要功能包括：")
para("（1）质评计划维护：记录计划的机构、年份、批次、包含项目与上报截止日期；", indent=True)
para("（2）成绩录入与查询：录入各批次质评成绩，支持按机构、年份、项目组合检索；", indent=True)
para("（3）合格判定与统计：依据成绩自动统计合格率，辅助科室掌握质评通过情况；", indent=True)
para("（4）计划批量导入：支持通过 Excel 模板批量导入质评计划与成绩。", indent=True)
para("该模块是室间质评工作的基础数据载体，为后续报告解析、单位校正与总结生成提供数据支撑。")
placeholder("室间质评计划列表页（含成绩录入/查询）")

heading("3.2 成绩单位换算与校正", 2)
para("针对部分项目仪器输出原单位、上报需转换为规定单位的情况，本模块提供单位换算与校正，主要功能包括：")
para("（1）换算因子表：按项目维护单位换算因子；", indent=True)
para("（2）按项目名 / 别名匹配：依据项目名称及其同义词自动识别需换算项；", indent=True)
para("（3）上报单位自动覆盖：按因子完成换算后，将上报单位值自动校正，降低人工填报错误。", indent=True)
para("该模块解决了内分泌激素等项目中因单位不一致导致上报错误的真实痛点。")

heading("3.3 质评报告自动解析", 2)
para("本模块从室间质评机构下发的报告正文中抽取结果数据，主要功能包括：")
para("（1）正文结构化解析：从非结构化质评报告文本中抽取各项目成绩；", indent=True)
para("（2）不依赖别名录入：直接基于报告原文解析，避免因别名差异导致的录入错位；", indent=True)
para("（3）解析结果校验：对抽取结果进行一致性校验，便于人工复核。", indent=True)
para("该模块将传统人工逐条录入质评结果的过程自动化，提升录入效率与准确性。")
placeholder("质评报告解析 / 单位换算校正页")

heading("3.4 项目与计划别名消歧匹配", 2)
para("检验项目存在缩写与同义词歧义（如 Tg 与 TG、IgG 与相关项目），本模块提供别名消歧匹配，主要功能包括：")
para("（1）别名归一化：将同一项目的不同别名归一到主项；", indent=True)
para("（2）歧义约束：对易混淆缩写设置匹配约束，避免错误关联；", indent=True)
para("（3）关联维护：在质评项目与计划之间建立准确的对应关系。", indent=True)
para("该模块保障了质评结果与项目的准确关联，是数据正确性的关键环节。")

heading("3.5 质评总结报告生成", 2)
para("本模块依据质评成绩与判定结果，自动生成室间质评总结报告，主要功能包括：")
para("（1）模板化生成：基于既定模板自动填充成绩、合格率与结论；", indent=True)
para("（2）报告导出：生成可归档的文档，便于科室留存与评审调阅；", indent=True)
para("（3）历史归档：对历次总结报告进行版本留存，支持追溯。", indent=True)
para("该模块将质评总结由人工撰写转为自动生成，显著降低文书工作量。")

heading("3.6 仪器间比对管理（WS/T 403—2024）", 2)
para("本模块依据卫生行业标准 WS/T 403—2024 开展仪器间比对与偏倚判定，主要功能包括：")
para("（1）偏倚计算：按标准公式计算测定值与参考值的偏倚百分比；", indent=True)
para("（2）允许总误差判定：依据标准允许总误差表判定比对是否可接受；", indent=True)
para("（3）分级判定：支持按水平、按测量程序细分判定规则；", indent=True)
para("（4）比对报告生成：自动生成仪器间比对报告，记录偏倚与判定结论。", indent=True)
para("该模块规范了仪器间比对的判定流程，确保判定一致、结果可追溯。")
placeholder("仪器间比对报告页（WS/T 403 偏倚判定）")

heading("3.7 室间比对管理（WS/T 415—2024）", 2)
para("本模块依据卫生行业标准 WS/T 415—2024 开展无 EQA 覆盖项目时的室间比对，主要功能包括：")
para("（1）定量结果偏倚与通过判定：按标准计算偏倚并执行通过比例判定；", indent=True)
para("（2）定性结果符合率：计算定性项目的结果符合率；", indent=True)
para("（3）双系统比较：支持同一标本多检测系统的比较分析；", indent=True)
para("（4）比对报告生成：自动生成室间比对报告。", indent=True)
para("该模块填补了无室间质评项目时的比对管理空白，满足 ISO 15189 合规要求。")
placeholder("室间比对报告页（WS/T 415 符合率）")

heading("3.8 多源质量目标综合比对", 2)
para("本模块汇集多来源质量目标并统一管理，主要功能包括：")
para("（1）多源目标同表：将不同来源的质量目标汇总于同一张对照表；", indent=True)
para("（2）目标检索与对照：支持按项目检索并对照不同来源的目标值；", indent=True)
para("（3）辅助判定：为比对与质评判定提供统一的质量目标依据。", indent=True)
para("该模块帮助科室在同一视图下掌握质量目标，避免多头维护造成的不一致。")

heading("3.9 权限控制", 2)
para("系统基于 RBAC（基于角色的访问控制）模型，按角色分配各功能模块的访问与操作权限，"
     "确保质评与比对数据仅对授权人员可见、可改，满足实验室信息安全与受控管理要求。")

# ===== 4 操作流程 =====
heading("4 软件操作流程", 1)
para("（一）登录系统：用户在浏览器输入系统地址，使用授权账号登录。")
para("（二）进入室间质评模块：在导航菜单中选择“室间质评”，进入计划与成绩列表页；"
     "可新增计划、录入成绩、执行单位换算校正。")
para("（三）解析质评报告：上传或粘贴质评报告正文，系统自动解析抽取结果并经人工复核。")
para("（四）维护别名匹配：在关联管理页核对项目与计划的别名匹配，确保准确关联。")
para("（五）生成质评总结：在总结生成页一键生成并导出室间质评总结报告。")
para("（六）开展仪器间比对：在比对模块录入测定与参考值，系统按 WS/T 403 计算偏倚并判定，生成报告。")
para("（七）开展室间比对：对无 EQA 项目录入室间比对数据，系统按 WS/T 415 判定并生成报告。")
para("（八）查询质量目标：在质量目标页检索并对照多源质量目标。")
placeholder("质评报告解析 / 总结报告生成页")

# ===== 5 数据与接口说明 =====
heading("5 数据处理与接口说明", 1)
para("（一）数据存储：室间质评、比对与质量目标数据统一存储于 MySQL 关系型数据库，"
     "通过 SQLAlchemy ORM 访问，保证数据一致性与完整性。")
para("（二）导入接口：提供 Excel 模板导入接口，前端校验后由后端解析入库，支持去重与错误提示。")
para("（三）解析与计算：质评报告解析、单位换算、偏倚与符合率计算均通过后端正则与规则引擎实现，"
     "结果经人工复核后入库。")
para("（四）安全与留痕：关键操作记录操作人、时间，支持审计追溯。")

# ===== 6 故障与维护 =====
heading("6 常见维护说明", 1)
para("（一）质评周期提醒：管理员应在每批次上报截止前完成成绩录入与总结生成。")
para("（二）数据备份：建议定期对 MySQL 数据库进行备份，防止数据丢失。")
para("（三）版本升级：本软件采用容器化部署，升级时通过更新镜像并保留数据库实现平滑迭代。")

doc.add_paragraph()
end = doc.add_paragraph()
r = end.add_run("— 本说明书对应软件版本 V1.0，最终解释权归著作权人所有 —")
set_cn(r, "宋体", 9)
r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
end.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.save(OUT)
print("saved:", OUT)
