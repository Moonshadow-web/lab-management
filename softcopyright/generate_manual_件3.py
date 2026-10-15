# -*- coding: utf-8 -*-
"""生成件③《检验科生化免疫组室内质控与靶值管理软件》软件说明书(用户手册) Word 文档。
含运行环境、功能模块详述、操作流程、4 个界面截图占位框，版面可满足软著≥15页要求。
著作权人按件①实际申报名义统一为：金子铮（个人）。
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = os.path.join(os.path.dirname(__file__), "件3_说明书.docx")

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
r = title.add_run("检验科生化免疫组\n室内质控与靶值管理软件\n软件说明书（用户手册）")
set_cn(r, "黑体", 20, bold=True)

doc.add_paragraph()
info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = info.add_run("软件全称：检验科生化免疫组室内质控与靶值管理软件\n"
                 "软件简称：室内质控与靶值管理软件\n"
                 "版本号：V1.0\n"
                 "著作权人：金子铮\n"
                 "开发完成日期：2026-06-30\n"
                 "开发方式：独立开发")
set_cn(r, "宋体", 12)

doc.add_page_break()

# ===== 1 软件概述 =====
heading("1 软件概述", 1)
para("检验科生化免疫组室内质控与靶值管理软件（简称：室内质控与靶值管理软件）是面向医院检验科"
     "生化免疫专业组开发的实验室信息管理系统子系统，用于统一管理日常室内质量控制数据与质控品靶值，"
     "支撑 ISO 15189 医学实验室质量和能力认可对检验结果精密度与正确度的受控要求。")
para("本软件采用 B/S（浏览器/服务器）架构，用户通过浏览器即可访问，无需安装客户端。"
     "系统对每日质控测定值进行多规则判定、对质控品换批进行累计靶值确立，并自动生成月度质控总结报告，"
     "实现室内质控工作的信息化、规范化、可追溯管理。")

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

heading("3.1 质控数据录入与管理", 2)
para("本模块用于录入与维护各检测系统的每日室内质控测定值，主要功能包括：")
para("（1）多水平质控管理：支持同一质控品不同浓度水平（如水平 1、水平 2）的测定值分别录入；", indent=True)
para("（2）日质控值录入：按检测系统、项目、批号、日期录入测定值；", indent=True)
para("（3）数据查询与导出：支持按项目、时间段、检测系统组合检索与导出。", indent=True)
para("该模块是室内质控的数据基础，为后续规则判定与靶值累计提供原始数据。")
placeholder("质控日数据列表 / 失控判定页（QCList）")

heading("3.2 Westgard 多规则判定引擎", 2)
para("本模块基于 Westgard 多规则对每日质控数据进行失控判定，主要功能包括：")
para("（1）经典规则判定：实现 1-2S、1-3S、2-2S、R-4S、10-X 等 Westgard 规则的自动判定；", indent=True)
para("（2）跨水平 R-4S 归一化：对高低浓度不同水平的相邻测定值，先按本水平靶值归一化为 z 值，"
     "再判定 |z 差| > 4，消除因浓度差异造成的伪 R-4S 误判；", indent=True)
para("（3）失控点冻结：已判定失控的点即时标记并冻结，不参与后续相邻对判定，避免级联污染；", indent=True)
para("（4）严重度合并：按规则严重度合并判定结论（如 1-3S 覆盖 1-2S）。", indent=True)
para("该模块将传统依靠检验人员肉眼判读质控图的工作自动化，提升判定一致性与效率，"
     "是其核心功能之一。")

heading("3.3 多源规则冲突消解", 2)
para("当质控数据由 LIS 导出并带规则标注时，本模块处理后端统计判定与 LIS 声明值之间的冲突，主要功能包括：")
para("（1）规则列覆盖：若 LIS 导出含规则列，以 LIS 声明值覆盖后端 Westgard 计算；", indent=True)
para("（2）空单元格与不可解析区分：严格区分“真正空单元格”（LIS 未标失控，判定为在控并冻结其 R-4S）"
     "与“有内容但解析不出有效规则码”（保留后端计算，避免误翻成在控）；", indent=True)
para("（3）异形标点归一化：对全角/无连字符等非常规写法进行归一化解析。", indent=True)
para("该模块解决了仪器声明状态与统计推导状态不一致导致的“假在控翻转”风险，是其方法特色之一。")

heading("3.4 累计靶值管理", 2)
para("本模块用于质控品换批时靶值的确立与维护，主要功能包括：")
para("（1）即刻法累计：依据 SI 界值表对累计测定值进行即刻法判定，快速初步确立靶值；", indent=True)
para("（2）常规法确立：当累计测定次数达到常规要求（如 n=20）后，以均值 ± SD 确立常规靶值与控制限；", indent=True)
para("（3）换批管理：记录质控品批号更换，分别维护各批号的靶值与 SD；", indent=True)
para("（4）失控值处理：对失控测定值进行标记保留，不自动舍去，保证统计严谨。", indent=True)
para("该模块规范了质控品换批靶值确立流程，符合 ISO 15189 与 Westgard 准则。")
placeholder("累计靶值看板页（TargetValueBoard）")

heading("3.5 质控物管理", 2)
para("本模块管理室内质控所用的质控品，主要功能包括：")
para("（1）质控物台账：维护质控品名称、批号、浓度水平、有效期；", indent=True)
para("（2）效期提醒：对临近过期的质控品进行预警；", indent=True)
para("（3）关联绑定：将质控品与对应检测项目、检测系统建立关联。", indent=True)
para("该模块保障了质控物信息的可追溯，是靶值管理与质控判定的基础。")
placeholder("质控物管理列表页（含效期/批号）")

heading("3.6 质控月结与总结报告", 2)
para("本模块对每月质控数据进行汇总并生成总结报告，主要功能包括：")
para("（1）月结统计：按月汇总各项目的测定次数、均值、SD、CV%、失控点数；", indent=True)
para("（2）报告生成：依据既定模板自动生成月度质控总结文档，记录累计靶值与失控处理情况；", indent=True)
para("（3）历史归档：对历次月结报告进行版本留存，支持追溯。", indent=True)
para("该模块将月度质控文书由人工撰写转为自动生成，显著降低文书工作量。")
placeholder("质控月结报告生成页（含 CV%/失控点汇总）")

heading("3.7 权限控制", 2)
para("系统基于 RBAC（基于角色的访问控制）模型，按角色分配各功能模块的访问与操作权限，"
     "确保质控数据仅对授权人员可见、可改，满足实验室信息安全与受控管理要求。")

# ===== 4 操作流程 =====
heading("4 软件操作流程", 1)
para("（一）登录系统：用户在浏览器输入系统地址，使用授权账号登录。")
para("（二）录入日质控数据：在质控模块按检测系统、项目、水平录入每日测定值。")
para("（三）查看失控判定：系统自动执行 Westgard 多规则判定，标记失控点并冻结级联。")
para("（四）处理 LIS 导入冲突：导入 LIS 数据时，系统按规则列与统计判定进行冲突消解。")
para("（五）确立累计靶值：在靶值看板页查看即刻法/常规法靶值确立进度，完成换批靶值维护。")
para("（六）管理质控物：维护质控品批号、效期与关联，处理过期预警。")
para("（七）生成月结报告：在月结模块一键生成并导出月度质控总结报告。")
placeholder("质控月结报告 / 靶值看板页")

# ===== 5 数据与接口说明 =====
heading("5 数据处理与接口说明", 1)
para("（一）数据存储：质控测定值、靶值、质控物与月结数据统一存储于 MySQL 关系型数据库，"
     "通过 SQLAlchemy ORM 访问，保证数据一致性与完整性。")
para("（二）导入接口：提供 LIS 数据导入接口，前端校验后由后端解析入库，支持规则列解析与去重。")
para("（三）判定与计算：Westgard 规则判定、跨水平归一化、累计靶值（即刻法/常规法）计算均通过后端正则与规则引擎实现，"
     "结果经人工复核后入库。")
para("（四）安全与留痕：关键操作记录操作人、时间，支持审计追溯。")

# ===== 6 故障与维护 =====
heading("6 常见维护说明", 1)
para("（一）质控频次提醒：管理员应按规定频次完成每日质控测定值录入与判定。")
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
