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
