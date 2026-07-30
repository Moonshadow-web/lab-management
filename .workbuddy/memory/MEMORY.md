# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 思路排查）。
- 管理员 金子铮(id=2)，登录 jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。

## 部署铁律（铁律）
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`
  - 第1提示回车选默认 No(自动切流量)；第2提示喂 Y 取消冲突任务。旧 `printf 'Y\n'` 误选灰度→流量不切换。
  - 构建源=origin/main（先 push）；就绪看 `curl /api/v1/_diag/build` 返回 200。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；公网 418=CDN不转发；勿反复 deploy（每次新 pod）。
- **每次改模型/解析/关键逻辑提交，必须同步改 `diag._BUILD_MARK`**（如 staff-education-2026-07-30）；部署后 `curl` 内网 `/api/v1/_diag/build` 核对标记——标记旧=未生效，**先问用户去控制台核真实情况**，不要自作主张取消灰度。
- **前端产物必须强提交进 git 才能上线**：`Dockerfile` 直接 `COPY frontend/dist`；`frontend/dist/` 在 `.gitignore` → 本地 `vite build` → `git add -f frontend/dist` → 提交推送 → 部署。核对前端上线：探测内网 `/assets/<Hash>.js` 200/旧 404。
- **多 AI 并发改 origin/main 会互相覆盖**：部署前 `git fetch` 核对远端 tip；被覆盖则重设 `_BUILD_MARK`、强提交 dist、再 deploy。

## 权限/前端铁律
- RBAC 逗号分隔；admin 通杀；30min access+7d refresh，401 静默 refresh；禁 Promise.all+静默 catch。
- 空白先要 F12 Console；沙箱浏览器被「风险提醒」拦截（curl 正常）。
- 权限 store：`let permStore` 提到函数作用域，勿在 try 内 const 后块外引用（ReferenceError 炸白）。
- 仪器显示：「名称(model)」，空型号仅名称。

## 业务模块要点
- EQA：/api/v1/eqa-plans；北京机构 01110025/4731。
- 仪器 name 代号式归整：instruments.name=科室代号，model 原值；显示拼「名称（型号）」。
- comparison：权威 WS/T 403—2024 字典 services/comparison_report.py，新TE查字典勿写死。
- **Westgard 月结（2026-07-25 晚冻结规则）**：相邻对先各自按本水平靶值归一化 z=(value-target_mean)/target_sd，再判 |z_前-z_后|>4 触发 R-4s；跨天相邻只标后点(当天)失控，前点不标 R-4s 标记（警告仅由 1-2s 产生）。**已失控点冻结**：一旦判失控即只留存、不再参与后续任何规则（不参与 R-4s 相邻对、不打断 10-x 计数）。归一化消除高低浓度水平伪 R-4s。
- **上传表格规则列覆盖后端 Westgard（2026-07-26）**：LIS 含规则列→逐点覆盖后端，按严重度取最严重（1-3S>2-2S>R-4S>10-x>1-2S），1-3S 覆盖 1-2S；空单元格分两分支：①识别到规则列→真正空一律在控并冻结；②无规则列→回落后端。写法不被识别的单元格保持后端。**已失控/带解析规则的点整体冻结不参与跨水平 R-4s**。解析器兼容全角/异形标点/无连字符(13S/10X)。`_recalc` 可用新解析器重算已上传数据。原始串落 `qc_daily_values.uploaded_rule`，`rule_column_present` 落 `qc_monthly_summaries`。
- 文档预览：xlsx exceljs / docx mammoth / pdf 直。旧版 .doc(OLE2 头)存成 .docx 名→预览报错，已改按文件头判定。
- **文件存储 = 腾讯云 COS 云存储（根治 MySQL 内存告警）**：全平台 BLOB 已清零（documents 462→0, versions 413→0, comparison_attachments 19→0, interlab_attachments 12→0）。三层：上传先 COS→DB LONGBLOB→磁盘；下载 COS 302 重定向→get_bytes→BLOB→磁盘。凭据走 CloudBase 控制台环境变量不进 git。Bucket=`636c-cloud1-0gjhamv53ff2298d-1408547492` region=`ap-shanghai`。`put_object` 的 `ContentLength` 必须 str。Dockerfile 需 gcc/python3-dev 编译 crcmod。早期 pre-迁移丢失 ~12 个文档需重传。

## 排班(scheduling)模块
- 四表 SchedulingPost/Plan/Assignment/Config；状态枚举与岗位平行、post_id 可空。
- 夜班岗(group=night)科室录入不自动生成；发热白班(is_fever_day)固定人每4工作日一班；固定岗 preferred_people 优先级递减。
- 工作流：先批量录非白班约束→再生成白班（夜班人当天排除）。
- 种子 14 岗；前端 SchedulingList.vue 月视图矩阵+批量录入+岗位/计划/设置 tab。

## 提醒推送（仅 ServerChan/方糖）
- 站内+邮件+ServerChan 三路；SendKey 存接收人 wx_uid；每天 08:00 聚合推 1 条。分类 eqa_biochem_coag/eqa_immuno/calibration。

## DB/迁移铁律
- CloudBase MySQL（cynosdbmysql-ins-102awksb）；DATABASE_URL 在 cloudbaserc.json。
- 禁 DROP；新列 ADD COLUMN 幂等；**MySQL 下补列靠 `_ensure_missing_columns()`（遍历模型 ADD COLUMN）**，`_migrate_schema` 的 alters 仅 SQLite 生效。部署中断→补列没跑→`Unknown column`/500。
- max_allowed_packet 线上=1GB；字节存 LONGBLOB；图片经 services/attachment_compress 压缩。

## 试剂配送角色（reagent_delivery，2026-07-27）
- 仅「到货接收」界面；只能新建/改自己创建的收货单；不能删除/改他人；看不到工作台。
- 沿用 roles 逗号串+模块权限表：新增模块 `reagent-receivings`（默认 admin/reagent_manager/reagent_delivery）；`reagents` 仍仅 admin/reagent_manager。
- 到货接收确认才入库：`create_receiving` 不写库存，`POST /receivings/{id}/confirm` 才累加；旧记录迁移回填 is_confirmed=1。

## 人员继教管理模块（2026-07-30 新增，进行中）
- 由旧「继教培训」改名（module_permission.py ALL_MODULES + router/index.js title 改「人员继教管理」），模块 key 仍 `training` 不动。
- 6 子功能：人员档案(生免室人员档案)、新员工培训(培训考核+独立上岗认证)、年度人员能力评估(含人员比对 BG-SM-CZ-023)、组内培训(年度计划+签到表打印/扫描上传+课件/通知/考题/效果评价存档)、实习进修带教、艾梅乙培训。
- 记录表格需用原表(1:1)；制度参考 MHZYY-SM-SOP-005。
- 模型集中放 `backend/app/models/education.py` + 附件表 `education_attachment`(LONGBLOB，复刻 comparison 附件模式)；`api/v1/education.py` 用 make_router + 通用附件端点。
