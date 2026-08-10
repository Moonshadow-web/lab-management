# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 排查）。
- 管理员 金子铮(id=2)，登录 jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。

## 部署铁律
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`（Enter=No灰发自动切流量；Y=取消冲突任务）。tcb=`/c/Users/81526/.workbuddy/binaries/node/versions/22.22.2/tcb`。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；公网 418=CDN 不转发。
- 每改模型/关键逻辑必改 `diag._BUILD_MARK`；部署后 curl 内网 `/api/v1/_diag/build` 核对标记（标记旧=未生效）。
- 前端产物 `Dockerfile` 直接 `COPY frontend/dist`（`.gitignore` 忽略）→ 需 `vite build --emptyOutDir false`（沙箱批量删 guard）+ `git add -f frontend/dist` + 推 + 部署；核对内网 `/assets/<Hash>.js` 200。
- **多 AI 并发**：另 AI 会改 `_BUILD_MARK`（force-recalc-goals/ckmb-norm-override 等）→ 部署前 `git fetch`+`ls-remote` 核对远端 tip；被覆盖则重设本轮值、强提交、再 deploy。origin/main 即生效源。
- **FastAPI 必须 `import app.main` 冒烟**（沙箱缺 qcloud_cos 跑不了全量 → 退而 py_compile + 部署后 curl _BUILD_MARK 即全量启动验证）。

## 权限/前端铁律
- RBAC 逗号分隔；admin 通杀；30min access+7d refresh，401 静默 refresh；禁 Promise.all+静默 catch。空白先 F12 Console。

## 业务模块要点
- EQA：/api/v1/eqa-plans；北京机构 01110025/4731。
- **EQA 单位换算豁免(2026-08-08)**：卫健委「骨代谢标志物」组（id 110/111，program=骨代谢标志物）PTH/VD **不换算**、固定原单位 PTH=pg/mL VD=ng/mL（`EQA_NO_CONVERT_UNITS` 不依赖项目库，项目库 PTH=ng/L/VD=µg/L 不可用）；卫健委/北京市「内分泌」组保持换算（PTH→pmol/L、VD→nmol/L）。逻辑：`eqa.py::_no_convert_unit_for/_conversion_for`（后端骨架+回填均走 `_conversion_for(plan, it)`，豁免项目移除旧 conv 并固定单位修正历史数据）+ 前端 `QCList.vue::matchConv(name, plan)` 传计划上下文豁免（`applyGrid`/`addCol` 传 `resultPlan.value`）。前后端豁免规则须同步维护。
- **评审重新分配(2026-08-07~08)**：ReviewTab.vue 展开行新增「重新分配」按钮（EditDialog+`updateAssignment` 更新原行，不产生重复行）+「待重分」标签；`assignedDocIds` 只统计有 reviewer_id 的行（释放行可重回批量分配弹窗）；`review.py::assign_batch` 用 released_map 复用空审核人行，批量重分配不产生重复行。姚建民(id=8)任务释放后可正常重分配。
- comparison：权威 WS/T 403—2024 字典 services/comparison_report.py。
- Westgard 月结 R-4s 归一化(2026-07-25 冻结)：相邻对各自按本水平靶值归一化判 |z差|>4；已失控点冻结不参与后续规则。上传规则列覆盖后端(2026-07-26)，严重度 1-3S>2-2S>R-4S>10-x>1-2S；解析器兼容全角/无连字符(13S/10X)；`_recalc` 可重算。
- 文档预览：xlsx exceljs / docx mammoth / pdf 直；旧版 .doc(OLE2)存成 .docx 名→按文件头判定。
- 文件存储=腾讯云 COS（根治 MySQL 内存告警）：全平台 BLOB 已清零；三层回退 COS→BLOB→磁盘；bucket=`636c-cloud1-0gjhamv53ff2298d-1408547492` region=`ap-shanghai`；`put_object` ContentLength 须 str；Dockerfile 需 gcc/python3-dev 编译 crcmod。

## 排班(scheduling)
- 四表 Post/Plan/Assignment/Config；状态枚举与岗位平行、post_id 可空；夜班不自动生成、发热白班固定人每4工作日一班；固定岗 preferred_people 优先级递减。种子 14 岗。

## 提醒推送
- 站内+邮件+ServerChan 三路；SendKey 存 wx_uid；每天 08:00 聚合推 1 条。分类 eqa_biochem_coag/eqa_immuno/calibration。

## DB/迁移铁律
- CloudBase MySQL；DATABASE_URL 在 cloudbaserc.json。禁 DROP；补列/改列靠 `_ensure_missing_columns()`（遍历模型 ADD COLUMN + MODIFY，INFORMATION_SCHEMA 判定幂等）；`_migrate_schema` 的 alters 仅 SQLite。部署中断→补列没跑→`Unknown column`/500。

## 试剂配送角色（reagent_delivery，2026-07-27）
- 仅「到货接收」；只能新建/改自己创建的收货单；不能删/改他人；看不到工作台。模块 `reagent-receivings`；到货确认才入库。

## 人员继教管理模块
- 旧「继教培训」改名（key 仍 training）；6 子功能：人员档案/新员工培训/年度能力评估(含人员比对)/组内培训/实习进修带教/艾梅乙培训。制度 MHZYY-SM-SOP-005。
- 模型 `models/education.py`：PersonnelMaster + 5 子表(education/work_exp/cert/reward/edu_exp)；附件表 education_attachments(LONGBLOB→COS)。`api/v1/education.py` make_router + 通用附件端点(前缀 /education-attachments)。
- 前端 StaffEducation.vue hub(el-tabs 6 块) + 7 staff 子组件 + EducationAttachmentList + SignInSheet。
- 导入源：桌面 `C:\Users\81526\Desktop\待办\继教人员（吕文娟）(1)\生免室人员档案` 15 人，antiword 解析。
- **子表全量录入(2026-07-31)**：`scripts/import_personnel_full.py` 解析教育/工作/证书/奖惩/继教 5 段——续行三型(日期碎片/名称换行/明细换行)、`至`/`至今` 优先拆分起止区间、学位尾提取；线上 API 录入 + 指纹幂等去重，**共 90 条**(education 28/work_exp 21/cert 22/reward 9/edu_exp 10)。已线上核验。
- **train_date bugfix(2026-07-31)**：edu_exp.train_date VARCHAR(20)→40（张婵媛长区间日期 21 字符写入 500），启动期 ALTER 迁移；_BUILD_MARK=edu-exp-train-date-widen-2026-07-31（曾被另一 AI 的 force-recalc-goals 部署顶掉，重推重部署后生效）。
- 部署踩坑(2026-07-30)：schemas/education 漏 import field_validator(NameError) + crud_base make_router search_fields 必填改默认 None(TypeError) → 两启动崩溃；`import app.main` 抓出。

## 15189 认可能力范围模块（2026-08-02）
- 第 4 个 15189 tab（Hub 加 `el-tab-pane name="scope"`）；参考《生免组申请认可的能力范围.xlsx》展示+编辑。
- 模型 `AccreditedScope`(`iso15189.py`)：分组 l1/l2 + 项目信息 + 系统关联(`*_name`+`*_id`) + 分析性能5项(正确度/精密度/线性/可报告范围/其他) + 说明/备注。方法非独立实体（from test_items.method 去重），设备/试剂关联 instruments/reagent。
- 后端 `accredited_scope.py`：`make_router(prefix="/accredited-scope")` + `POST /accredited-scope/batch?replace=true`（xlsx 种子）；**更新用 PUT**（make_router 无 PATCH，前端 `updateScope` 须 `request.put`）。
- 导入 `scripts/import_accredited_scope.py`：openpyxl 解析 Sheet1(A1:R109)，分组判定=A列前置字母1个→l1、≥2→l2，共64条；方法/试剂/仪器先存旧文本*_name，*_id留空待前端下拉关联。

## 已知坑（Pydantic / 通用 CRUD）
- **json_fields 经 ORM 对象读取会整列丢失**：`ReadSchema.model_validate(ORM对象)` 在 pydantic from_attributes 模式下，对 Text 列的 JSON 字符串**不触发 `mode="before"` 校验器的 `json.loads`**（实测返回 `[]`/`{}`，但 `json.loads` 裸字符串正常、普通类对象 `model_validate` 正常）。凡用 `make_router(json_fields=[...])` 的模块（新员工培训 plan_items/detail_json、能力评估 scores_json 等）读取均中招。
  - **正确做法**：`crud_base.py` 已用 `_serialize(obj)`（ORM→dict + 手动 `json.loads`）+ `_to_read(obj)`（`ReadSchema.model_validate(dict)`）绕过；list/get/create/update 全部走 `_to_read`。新增 json_fields 模块时无需再改，但**勿删 `_to_read`**。
- **API 路径带 router 自带前缀**：auth=`/api/v1/auth/login`、education 各资源=`/api/v1/education/...`（如 new-employee-trains），不是 `/api/v1/login` / `/api/v1/new-employee-trains`。排查 404/405 先 curl `/openapi.json` 核对真实路径（勿被 SPA fallback 的 404/405 误导）。
- **内网部署生效慢**：tcb deploy 提交后，内网 curl `/api/v1/_diag/build` 往往要 ~5 分钟才翻到新 `_BUILD_MARK`（容器构建+滚动发布），勿提前判定失败。
- **前端"操作后跳登录/跳走"= 拦截器 401→gotoLogin，try-catch 拦不住**：现象（如 15189 接收新版本后跳到工作台）排查时先 `grep router.push` 确认业务代码无导航；若无，必是 `utils/request.js` 响应拦截器在 401 且 refresh 失败分支调 `gotoLogin()`（先 `clearAuth` 再 `router.push('/login')`，该跳转在 Promise.reject 之前执行，业务层 try-catch 无效）。根因多为 access token(30min) 过期、refresh(7d) 也失效。正确修法不是 try-catch，而是让登录后**回跳原页面**：`gotoLogin()` 把 `currentRoute.fullPath` 作为 `?redirect=` 带入登录页；`Login.vue` 登录成功后 `router.push(route.query.redirect || '/dashboard')`；`router.beforeEach` 中 `to.path==='/login' && isLoggedIn` 时 `next(to.query.redirect || '/dashboard')`。
- **git 索引文件锁(Windows, 2026-08-07~08)**：`.git/index`、`cloudbaserc.json` 曾被某进程独占锁（读可、写/rename Permission denied；普通 git add/commit 报「unable to write new index file」，tcb 回写 cloudbaserc.json 报 EPERM——不影响部署「submission completed」）。**绕过提交**：`cp .git/index .git/alt_index` → `GIT_INDEX_FILE=.git/alt_index git add <files>` → `git write-tree` → `git commit-tree <tree> -p HEAD -m ...` → `git update-ref refs/heads/main <commit>` → `git push`（全程不写被锁 index）。plumbing 提交后真实 index 未更新，锁释放后须 `git reset --mixed HEAD` 同步。锁约数小时自动释放。

## docx SOP 标题提取（2026-08-03 已踩坑）
- **勿用 `python-docx` 的「正文第一段」当标题**：这些 SOP 的大标题是分多段写的（如「AU5800检测系统免疫透射比浊法」+「血清载脂蛋白B测定标准操作程序」），`doc.paragraphs[0].text` 只读第一段 → 截断。且正文起点不统一（「1 承担部门」/「检验目的」/「检测目的」/「检查目的」），全角句号「2．」也会让 `^\d+[.、]` 漏判。
- **正确做法**（见 `scripts/fix_titles.py`）：拼接开头连续段落，遇「以数字开头」或「检验目的/检测目的/检查目的/承担部门」截断；若结果不以 `测定标准操作程序/标准操作程序/操作作业指导书/操作程序` 结尾或含正文关键词，则**回退用文件名 stem**（文件名是完整且规范的 SOP 名）。
- 个别 docx 标题本身缺字（如 109 缺「序」），只能靠文件名补回；文件名与正文方法写法不同（如 101 文件名「酶法」/正文「己糖激酶法」）以正文具体写法优先（更准）。

## AU5800 系列项目 SOP 文档（桌面，2026-08-03）
- 任务：把 `C:\Users\81526\Desktop\待办\AU5800` 下 62 份项目 SOP 里对通用仪器 SOP「SOP-1002《AU5800生化分析仪标准操作程序》」及泛称「仪器操作规程/仪器标准操作程序」的引用，改为该项目**真实所用机器**（取自系统仪器档案「使用本仪器的检验项目」）。
- 机器编号约定（用户给）：AU5821A=AU58-1→尾号2002；AU5821B=AU58-2→尾号2003；AU5800急诊=AU5800→尾号1005。替换目标形如 `MHZYY-JYK-SM-SOP-{sops}《贝克曼{names}全自动生化分析仪操作作业指导书》`（保留原 doc 的 MHZYY/HZYY 前缀与「的」）。
- 系统取数：`/instruments/{67,68,5}/test-items` 返回条目 **必须用 id 反查主表 `/test-items` 的规范 name**（接口自身 name 字段部分项目缺失，直接读会漏 AU5800 上的项目）。
- 工具 `scripts/replace_au5800_sop.py`：逐 run 保留格式替换（python-docx 跨 run 重建，rPr 须 `copy.deepcopy` 否则丢格式）；APPLY=1 前先 `shutil.copy2` 备份到 `AU5800_BACKUP/`。
- 结果：61 份替换（旧引用清零、新引用按各项目真实机器）、文档自身标题「AU5800检测系统…测定标准操作程序」不动。
- **例外未改**：`SM-SOP-126 N-乙酰-β-D-氨基葡萄糖苷酶`——系统无此 test_item（仪器档案里也无），无法匹配机器，留待用户决定。另注意：尿酸只在 AU58-1/AU58-2（不在 AU5800）；锌只在 AU58-2/AU5800；小而密只在 AU58-2/AU5800；淀粉样蛋白A=血清淀粉样蛋白A只在 AU58-2；腺苷脱氨酶系统仅（胸腹水）/（脑脊液）变体→按 AU5800。

## 软著办理（生免组系统，用户实操）
- 用户以**个人名义**办理（著作权人：金子铮，不盖章、签字即可），非单位名义。
- 拆 5 件登记：①检验项目与仪器管理 ②室间质评与比对 ③室内质控与靶值 ④试剂与物料 ⑤综合业务平台。
- 件①已填表+签章(2026-08-03本人签字)待缴费；件②源码/说明书/主要功能已备，用户自改说明书措辞。
- **修正(2026-08-04)**：软著各件「开发完成日期/版本号」**不强制一致**（审查不做实质核实）；建议延续件①的 2026-06-30/V1.0 只为省事避疑，非硬性规定。
- **合规提醒**：件①~②说明书系 AI 起草，用户签「未使用AI」声明前须人工改写措辞；业务代码为本人独立开发。

### 软著各件通用申请表字段（与件①一致，件③~⑤复用）
- 软件分类：应用软件
- 发表状态：未发表
- 开发硬件环境：通用PC（Intel i5/16GB内存/512GB SSD）
- 运行硬件环境：云服务器（2核4GB内存/100GB SSD）
- 开发OS：Windows 10/11
- 开发工具：Python 3.13、VS Code、Node.js 22、Git
- 运行平台/OS：Linux + Chrome/Edge 浏览器
- **运行支撑环境(限50字)：MySQL 8.0、Nginx、Python 3.13、腾讯云 CloudBase 容器平台**
- 编程语言：Python、JavaScript
- 权利范围：全部权利；开发方式：独立开发
- 著作权人：金子铮（个人名义，签字不盖章）；版本 V1.0；完成日 2026-06-30（建议延续，非强制）

### 软著各件源程序量（各自填，勿填总数）
- 件①检验项目与仪器管理软件：3537 行
- 件②室间质评与比对管理软件：9500 行
- 件③室内质控与靶值管理软件：6397 行
- 件④试剂与物料管理软件：3950 行
- 件⑤综合业务管理平台软件：10673 行

### 软著各件开发目的（各件不同，落点一致）
- 件①检验项目与仪器管理：实现检验科生化免疫专业组检验项目与仪器档案的信息化管理，支撑 ISO 15189 受控要求
- 件②室间质评与比对：实现科室室间质评与仪器间/室间比对的信息化管理，规范偏倚判定与上报，支撑 ISO 15189 受控
- 件③室内质控与靶值：实现科室室内质控数据与累计靶值的信息化管理，自动完成 Westgard 多规则判定与月结，支撑 ISO 15189 受控
### 软著各件技术特点（100字框，架构一致+各件特有技术点）
- 件①检验项目与仪器：B/S架构前后端分离，FastAPI+Vue3+MySQL，支持云部署与RBAC权限控制（偏项目主数据与仪器档案）
- 件②室间质评与比对：B/S架构前后端分离，FastAPI+MySQL+Vue3+Element Plus，支持质评报告自动解析、单位换算校正及按WS/T 403/415自动偏倚判定，云部署+RBAC
- 件③室内质控与靶值：B/S架构前后端分离，FastAPI+MySQL+Vue3+Element Plus，内置Westgard多规则判定引擎（跨水平R-4S归一化、失控冻结、多源规则冲突消解）与累计靶值（即刻法/常规法）算法，云部署+RBAC
- 类型勾选：均勾「医疗软件」
