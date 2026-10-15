# -*- coding: utf-8 -*-
"""生成件①《检验科生化免疫组检验项目与仪器管理软件》软件说明书(用户手册) Word 文档。
含运行环境、功能模块详述、操作流程、4 个界面截图占位框，版面可满足软著≥15页要求。
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = os.path.join(os.path.dirname(__file__), "件1_说明书.docx")

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
r = title.add_run("检验科生化免疫组\n检验项目与仪器管理软件\n软件说明书（用户手册）")
set_cn(r, "黑体", 20, bold=True)

doc.add_paragraph()
info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = info.add_run("软件全称：检验科生化免疫组检验项目与仪器管理软件\n"
                 "软件简称：检验项目管理软件\n"
                 "版本号：V1.0\n"
                 "著作权人：民航总医院\n"
                 "开发完成日期：2026-06-30\n"
                 "开发方式：独立开发")
set_cn(r, "宋体", 12)

doc.add_page_break()

# ===== 1 软件概述 =====
heading("1 软件概述", 1)
para("检验科生化免疫组检验项目与仪器管理软件（简称：检验项目管理软件）是面向医院检验科"
     "生化免疫专业组开发的实验室信息管理系统子系统，用于统一管理检验项目主数据与仪器档案，"
     "支撑 ISO 15189 医学实验室质量和能力认可对受控管理的要求。")
para("本软件采用 B/S（浏览器/服务器）架构，用户通过浏览器即可访问，无需安装客户端。"
     "系统管理检验科生化免疫专业组 120 余项检验项目的主数据，以及各专业仪器设备的台账、"
     "家族归组与技术档案，实现检验资源的信息化、规范化、可追溯管理。")

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

heading("3.1 检验项目管理", 2)
para("检验项目管理模块维护生化免疫专业组全部检验项目的主数据，主要功能包括：")
para("（1）项目新增、编辑、删除与查询：支持按项目名称、代码、方法学、单位等条件组合检索；", indent=True)
para("（2）项目主数据字段：项目名称、项目代码、英文缩写、方法学、检测系统、样本类型、"
     "单位、参考区间（含年龄/性别分层）、临床意义、注意事项等；", indent=True)
para("（3）批量导入与导出：支持通过 Excel 模板批量导入检验项目，并可将查询结果导出为 Excel；", indent=True)
para("（4）参考区间维护：支持按性别、年龄分段维护参考区间，满足不同人群的差异化管理需求。", indent=True)
para("该模块是整套实验室管理系统的基础数据源，为室间质评、室内质控、仪器比对等模块提供"
     "统一的项目主数据支撑。")
placeholder("检验项目列表页（含搜索/筛选）")

heading("3.2 仪器台账管理", 2)
para("仪器台账管理模块维护生化免疫专业组各台仪器设备的台账信息，主要功能包括：")
para("（1）仪器基本信息：仪器名称、型号、序列号、生产厂家、启用日期、安装地点、负责人；", indent=True)
para("（2）仪器状态管理：在用、停用、维修、报废等状态标识；", indent=True)
para("（3）检定 / 校准管理：记录检定与校准周期，系统对临近到期仪器给出提醒，确保量值溯源有效；", indent=True)
para("（4）仪器查询：支持按名称、型号、状态、地点等多条件检索。", indent=True)
para("该模块帮助科室建立完整的仪器资产档案，是 ISO 15189 设备管理的核心载体。")
placeholder("仪器台账列表页")

heading("3.3 仪器家族管理", 2)
para("仪器家族管理模块将同型号、同规格的多台仪器归并为一个家族进行统一管理，主要功能包括：")
para("（1）家族创建与维护：定义家族名称、型号、关联的多台具体仪器；", indent=True)
para("（2）家族级配置：在家族层面维护共性参数，减少逐台重复配置；", indent=True)
para("（3）成员管理：支持将仪器加入或移出某一家族。", indent=True)
para("该模块便于对多台同类仪器进行批量管理与横向比对。")

heading("3.4 仪器档案管理", 2)
para("仪器档案管理模块管理每台仪器的技术档案附件，主要功能包括：")
para("（1）档案上传：上传标准操作程序（SOP）、检定 / 校准证书、维护记录、性能验证报告等；", indent=True)
para("（2）版本管理：档案更新时保留历史版本，确保变更可追溯；", indent=True)
para("（3）档案查询与下载：按仪器、档案类型快速检索并调阅。", indent=True)
para("该模块实现了仪器技术资料的全生命周期电子化管理，替代传统纸质档案，便于现场评审与审计。")
placeholder("仪器档案详情与附件上传页")

heading("3.5 仪器文档关联", 2)
para("仪器文档关联模块支持将体系文件、记录表格等文档与具体仪器建立挂载关系，主要功能包括：")
para("（1）文档挂载：将相关 SOP、记录表与研究文档关联到对应仪器；", indent=True)
para("（2）关联查看：在仪器详情页直接查看其关联的全部文档；", indent=True)
para("（3）关联维护：支持新增、解除文档与仪器的关联关系。", indent=True)
para("该模块打通了文档与设备之间的关联，提升了体系文件的可达性与受控性。")

heading("3.6 权限控制", 2)
para("系统基于 RBAC（基于角色的访问控制）模型，按角色分配各功能模块的访问与操作权限，"
     "确保检验项目与仪器数据仅对授权人员可见、可改，满足实验室信息安全与受控管理要求。")

# ===== 4 操作流程 =====
heading("4 软件操作流程", 1)
para("（一）登录系统：用户在浏览器输入系统地址，使用授权账号登录。")
para("（二）进入检验项目模块：在系统导航菜单中选择“检验项目”，进入项目列表页；"
     "可进行查询、新增、编辑、导入导出等操作。")
para("（三）进入仪器管理模块：在导航菜单中选择“仪器”，进入仪器台账页；"
     "可维护仪器基本信息、状态、检定/校准周期。")
para("（四）维护仪器家族：在仪器家族页创建家族并将同类仪器归组。")
para("（五）上传技术档案：在仪器档案页上传 SOP、检定证书等附件，系统自动留痕版本。")
para("（六）关联文档：在文档关联页将体系文档挂载到对应仪器。")
para("（七）查询与维护：日常通过检索功能快速定位项目或仪器，进行持续维护。")
placeholder("项目编辑/导入对话框")

# ===== 5 数据与接口说明 =====
heading("5 数据处理与接口说明", 1)
para("（一）数据存储：检验项目、仪器、家族、档案等数据统一存储于 MySQL 关系型数据库，"
     "通过 SQLAlchemy ORM 进行访问，保证数据一致性与完整性。")
para("（二）导入接口：提供 Excel 模板导入接口，前端校验后由后端解析入库，支持去重与错误提示。")
para("（三）对外接口：本模块通过 RESTful API 向室间质评、室内质控、仪器比对等模块"
     "提供统一的项目主数据查询服务，避免主数据多头维护。")
para("（四）安全与留痕：关键操作记录操作人、时间，支持审计追溯。")

# ===== 6 故障与维护 =====
heading("6 常见维护说明", 1)
para("（一）检定到期提醒：系统按设定的校准周期自动计算到期日并提醒，管理员应及时安排检定/校准。")
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
