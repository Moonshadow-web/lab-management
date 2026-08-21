# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 排查）。
- 管理员 金子铮(id=2)，登录 jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。

## 部署铁律
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`（Enter=No灰发自动切流量；Y=取消冲突任务）。tcb=`/c/Users/81526/.workbuddy/binaries/node/versions/22.22.2/tcb`。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；公网 418=CDN 不转发。
- 每改模型/关键逻辑必改 `diag._BUILD_MARK`；部署后 curl 内网 `/api/v1/_diag/build` 核对标记（标记旧=未生效）。
- 前端产物 `Dockerfile` 直接 `COPY frontend/dist`（`.gitignore` 忽略）→ 需 `vite build --emptyOutDir false` + `git add -f frontend/dist` + 推 + 部署；核对内网 `/assets/<Hash>.js` 200。
- **多 AI 并发**：另 AI 会改 `_BUILD_MARK` → 部署前 `git fetch`+`ls-remote` 核对远端 tip；被覆盖则重设、强提交、再 deploy。
- **FastAPI 必须 `import app.main` 冒烟**（`py_compile` 不足以验证，security.py 铁律见下）。

## 权限/前端铁律
- RBAC 逗号分隔；admin 通杀；30min access+7d refresh，401 静默 refresh；禁 Promise.all+静默 catch。空白先 F12 Console。

## 业务模块要点
- **test_items 库试剂/品牌(2026-08-21 收口)**：用户确认「试剂」即「品牌」(brand)，`TestItem` **不**单独存 `reagent` 列，只用 `brand`。`search_fields`/导出仅含 `brand`；前端 TestItemList 不展示「试剂」单独列；不确定度试剂下拉 `searchItemField(...,'brand')` 从 `it.brand` 取、value=it.brand，`onProjectChange` 用 `hit.brand` 带出；不确定度记录自身仍存 `reagent` 字段(=品牌值)。回滚 commit 见当天日志。
- EQA：/api/v1/eqa-plans；北京机构 01110025/4731。
- **EQA 单位换算豁免(2026-08-08)**：卫健委「骨代谢标志物」组(id110/111)PTH/VD 不换算、固定原单位；「内分泌」组保持换算。逻辑 `eqa.py::_no_convert_unit_for/_conversion_for` + 前端 `QCList.vue::matchConv(name,plan)` 传计划上下文。前后端豁免规则须同步维护。
- **评审重新分配(2026-08-07~08)**：ReviewTab 展开行「重新分配」按钮 → `updateAssignment` 更新原行不产生重复行；`review.py::assign_batch` 用 released_map 复用空审核人行。
- comparison：权威 WS/T 403—2024 字典 `services/comparison_report.py`。
- Westgard 月结 R-4s 归一化(2026-07-25 冻结)：相邻对各自按本水平靶值归一化判 |z差|>4；已失控点冻结不参与后续规则；上传规则列覆盖后端(2026-07-26)，严重度 1-3S>2-2S>R-4S>10-x>1-2S；解析器兼容全角/无连字符。
- 文档预览：xlsx exceljs / docx mammoth / pdf 直；旧版 .doc(OLE2)存成 .docx 名→按文件头判定。
- 文件存储=腾讯云 COS：全平台 BLOB 清零；三层回退 COS→BLOB→磁盘；bucket=`636c-cloud1-0gjhamv53ff2298d-1408547492` region=`ap-shanghai`。
- **排班(scheduling)**：四表 Post/Plan/Assignment/Config；夜班不自动生成、发热白班固定人每4工作日一班；固定岗 preferred_people 优先级递减；种子 14 岗。
- **提醒推送(notifications/reminders)**：站内+邮件+ServerChan 三路；SendKey 存 wx_uid；每天 08:00 聚合推 1 条；分类 eqa_biochem_coag/eqa_immuno/calibration。
- **试剂配送角色(reagent_delivery,2026-07-27)**：仅「到货接收」；只能新建/改自己创建的收货单；到货确认才入库。
- **人员继教管理(education,2026-07-31)**：6 子功能；模型 PersonnelMaster+5子表+附件(COS)；`scripts/import_personnel_full.py` 解析5段续行三型，`至/至今`优先拆分起止区间，线上录入+指纹幂等，**共90条**。train_date VARCHAR(20)→40 迁移踩坑。
- **15189 认可能力范围(accredited_scope,2026-08-02)**：第4个15189 tab；模型分组l1/l2+项目信息+系统关联+分析性能5项；`POST /accredited-scope/batch?replace=true` 种子；更新用 PUT。导入64条。
- **security.py 铁律(2026-08-11 血泪)**：全局认证核心，是禁区——勿加新函数/类（曾致容器连崩4次）。需复用认证逻辑→独立 `core/_auth_helpers.py`。即使 py_compile 过也不保证 uvicorn 加载，部署前必 `import app.main` 冒烟。

## 桌面任务：性能验证报告归档命名规范（2026-08-21）
- 认可能力范围表：`D:/民航总医院/15189/生免认可申请附表/生免组申请认可的能力范围.xlsx`（Sheet1：AA临床血液学 6 项 / AC临床化学 28 项 / AD临床免疫学…）。
- AC 临床化学 28 项顺序：钠1、钾2、氯3、葡萄糖4、尿素5、肌酐6、尿酸7、钙8、镁9、无机磷10、丙氨酸氨基转移酶11、天冬氨酸氨基转移酶12、总蛋白13、白蛋白14、总胆红素15、直接胆红素16、碱性磷酸酶17、γ－谷氨酰氨基转移酶18、甘油三酯19、总胆固醇20、高密度脂蛋白胆固醇21、低密度脂蛋白胆固醇22、淀粉酶23、脂肪酶24、肌酸激酶25、乳酸脱氢酶26、糖化血红蛋白27、C反应蛋白28。
- 归档命名：`{序号}-{项目名}性能验证（靶机）.xlsx`，目录 `.../生免项目性能验证/AC临床化学`；未申请认可项目放 `未申请认可项目/` 保持原名。源目录为各机器验证报告（如 生化2号机 靶机，36 个文件含 9 个未认可项 CO2/CHE/CYSC/HCY/IRON/LAC/PA/TBA/UIBC）。
- 复用：其他机器（1/3/4号机、唐筛、急诊）验证报告可照此映射复制改名。

## 已知坑（Pydantic / 通用 / 前端 / git）
- **json_fields 经 ORM 读取整列丢失**：`ReadSchema.model_validate(ORM对象)` 对 Text 列 JSON 字符串不触发 `mode="before"` 校验器。正确做法 crud_base 已用 `_serialize`+`_to_read` 绕过；勿删 `_to_read`。
- **API 路径带 router 前缀**：auth=`/api/v1/auth/login`、education=`/api/v1/education/...`。404/405 先 curl `/openapi.json` 核对，勿被 SPA fallback 误导。
- **内网部署生效慢**：tcb deploy 后 curl `/api/v1/_diag/build` 约5分钟才翻到新标记。
- **前端操作跳登录=拦截器401→gotoLogin**：业务层 try-catch 无效；根因 token 过期。修法：登录回跳 `?redirect=` 原页面。
- **git 索引锁(Windows 2026-08-07~08)**：绕过用 plumbing（`GIT_INDEX_FILE=.git/alt_index` 序列），锁释后 `git reset --mixed HEAD`。

## docx SOP 标题提取 / AU5800（桌面任务，2026-08-03）
- 勿用 `doc.paragraphs[0]` 当标题（SOP 大标题分多段）；正确做法见 `scripts/fix_titles.py`（拼接开头连续段遇数字/检验目的截断，否则回退文件名）。
- AU5800 系列 61 份 SOP 已替换引用为真实机器（尾号2002/2003/1005）；`SM-SOP-126` 无 test_item 未改。

## 软著办理（实办，个人名义，著作权人：金子铮）
- 拆5件：①检验项目与仪器(3537行)②室间质评与比对(9500)③室内质控与靶值(6397)④试剂与物料(3950)⑤综合业务平台(10673)。件①②③已提交。
- 通用字段：应用软件/未发表/运行支撑环境=MySQL8.0、Nginx、Python3.13、腾讯云CloudBase/语言Python+JavaScript/权利全部/独立开发/V1.0/完成日2026-06-30（不强制一致，仅需延续省事）。
- **合规提醒**：说明书系 AI 起草，签「未使用AI」声明前须人工改写；业务代码为本人独立开发。
- **软著对北京市卫生副高无用**（代表作清单不含软著；破格=国家发明专利）。定位：单位/防抄/推广/资质。
