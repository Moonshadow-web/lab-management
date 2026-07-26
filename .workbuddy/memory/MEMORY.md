# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 思路排查）。
- 管理员 金子铮(id=2)，登录 jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。

## 部署（铁律）
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`
  - 第1提示回车选默认 No(自动切流量)；第2提示喂 Y。旧 `printf 'Y\n'` 误选灰度→流量不切换。
  - 构建源=origin/main（先 push）；就绪看 `curl /api/v1/_diag/build` 返回 200。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；公网 418=CDN不转发；勿反复 deploy（每次新 pod）。

## 权限/前端铁律
- RBAC 逗号分隔；admin 通杀；30min access+7d refresh，401 静默 refresh；禁 Promise.all+静默 catch。
- 空白先要 F12 Console；沙箱浏览器被「风险提醒」拦截（curl 正常）。
- 权限 store：`let permStore` 提到函数作用域，勿在 try 内 const 后块外引用（ReferenceError 炸白）。
- 仪器显示：「名称(model)」，空型号仅名称。

## 业务模块要点
- EQA：/api/v1/eqa-plans；北京机构 01110025/4731。
- 仪器 name 代号式归整(2026-07-23)：instruments.name=科室代号，model 原值；显示拼「名称（型号）」。
- comparison：权威 WS/T 403—2024 字典 services/comparison_report.py，新TE查字典勿写死。
- Westgard 月结 R-4s（2026-07-25 晚修订冻结）：相邻对先各自按本水平靶值归一化 z=(value-target_mean)/target_sd，再判 |z_前-z_后|>4 触发；**同一天两水平都失控(ooc)**，跨天相邻**只标后点(当天)失控**、前点不标任何 R-4s 标记（**警告仅由 1-2s 产生**，R-4s 不再产生警告）。**已失控点冻结**：一旦判失控(1-3s/2-2s/R-4s/10-x)即只留存、不再参与后续任何规则——不作为 R-4s 相邻对参与点，也不计入 10-x 连续同侧（失控点打断 10-x 计数）。归一化消除高低浓度水平(如甲肝IgM)因原始浓度差导致的伪 R-4s。表面抗原 06-13 案例：水平1 用错质控品得 0.441(1-3s 真实失控)，冻结后同天的在控 3.6 不再被误判 R-4s。
- **上传表格规则列覆盖后端 Westgard（2026-07-26，用户要求）**：若 LIS 导出含规则列（表头映射见 `_COLUMN_ALIASES.violate_rule`：失控规则/violateRule/westgard规则 等），该列**逐点覆盖**后端计算——同单元格多规则按严重度取最严重者（1-3S > 2-2S > R-4S > 10-x > 1-2S），**1-3S 覆盖 1-2S**（判失控、不标警告）；**空单元格的两种分支**：① 本次上传识别到规则列（`rule_column_present=True`）→ **真正空**的单元格**一律在控**（清空后端 ooc/警告，且该点一并冻结、不参与 R-4s）；② 上传无规则列 → 空单元格回落后端 Westgard。**关键**：有内容但写法不被解析器识别的单元格 → 保持后端 Westgard（绝不当成空单元格清零）。带成功解析的上传规则的点（失控或警告）**整体冻结、不参与跨水平 R-4s**。原始串落库 `qc_daily_values.uploaded_rule`；上传/`_recalc` 透传 `rule_column_present` 落库 `qc_monthly_summaries.rule_column_present`。**解析器兼容 LIS 变体**：全角/异形标点(－～–:)转半角、去外层括号、子串提取(1-3S(失控)/失控1-3S)、无连字符(13S/10X)。**修复踩坑(67033c3)**：曾把「解析失败」与「空」混为一谈，含规则列但写法不被识别的失控点被误清零（如 AU5800 的 β2微球蛋白 1-3S、10-x 消失）。上传响应含 `rule_column_matched` + `rule_cells_total/recognized/unrecognized` 诊断计数；修复后调用 `_recalc` 即可用新解析器重算已上传数据（无需重传，前提是当时规则列已被识别）。
- 文档预览：xlsx exceljs / docx mammoth / pdf 直。

## 排班(scheduling)模块（第三轮重构 2026-07-24）
- 四表 SchedulingPost(岗位)/SchedulingPlan(计划)/SchedulingAssignment(每日分配)/SchedulingConfig(配置)。
- 状态枚举：在岗/休息/病假/开会/行政/质控/教学（与岗位平行，**post_id 可空**；采血/卫生部门上经用户确认不存在，已移除）。
- 夜班岗(group=night)由科室提前录入，不自动生成；发热白班(is_fever_day)固定人每4工作日一班。
- 固定岗 preferred_people **优先级递减**（非轮转）；全部不可用才回退通用池。
- 工作流：先批量录入夜班/发热/休息等非白班约束 → 再生成白班；生成时夜班人员当天被排除。
- API：posts/plans/assignments CRUD + /generate + /cell(可空post upsert) + /batch(批量录入) + /grid(岗位行+状态行) + /my-today + /config。
- 种子 14 岗 + 排除[王学晶,李东,管理员,技术支持,访客]，main.ensure_scheduling_defaults 按 name upsert。
- 前端 SchedulingList.vue：月视图主页(日期列×岗位/状态行，桌面矩阵+移动端日卡，色标，点格编辑/删除)+批量录入+岗位/计划/设置 tab。
- 用户 Excel 排班表简写：秦=秦满红，芳=秦东芳（批量录入时展开）；本环境无法读取图片，历史排班需用户以 Excel/文字提供。

## 提醒推送（仅 ServerChan/方糖）
- WxPusher 通道已死(微信封禁)→已移除；现 站内+邮件+ServerChan(微信) 三路。
- SendKey 存接收人 wx_uid 字段，无需环境变量；每人每天免费≤5条，系统每天08:00聚合推1条。
- 接入：sctapi.ftqq.com 扫码关注→复制SendKey→接收人填 wx_uid+渠道 serverchan→发送测试。
- 分类(rule_categories)：eqa_biochem_coag / eqa_immuno / calibration。

## DB/迁移铁律
- 已切 CloudBase MySQL（cynosdbmysql-ins-102awksb）；DATABASE_URL 在 cloudbaserc.json。
- 禁 DROP；新列 ADD COLUMN 幂等；老列放宽用 ALTER ... DROP NOT NULL；诊断端点只 /build 免鉴权。
- max_allowed_packet 实测线上=1GB，大文件上传已无 500；字节存 MySQL BLOB(LONGBLOB 16MB)，图片经 services/attachment_compress 压缩。
- **迁移生效机制**：`main._migrate_schema` 的 `alters` 字典**仅 SQLite 生效**（内部用 PRAGMA）；**MySQL 下补列完全靠 `_ensure_missing_columns()`（dialect 无关，遍历模型 ADD COLUMN）**。非空线上表新增模型列必须靠后者；若某次部署中断（如镜像推送 broken pipe），补列可能没跑 → 下一个引用新列的请求报 `Unknown column`/500。已在 `_ensure_missing_columns` 末尾对 QC 两列(`rule_column_present`/`uploaded_rule`)做**显式兜底补列**。

## 部署铁律（重申）
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`。第1提示回车选默认（自动切流量，不要进灰度）；第2提示喂 Y 取消冲突任务。旧 `printf 'Y\n'` 误选灰度→流量不切换。
- **每次改模型/解析/关键逻辑提交，必须同步改 `diag._BUILD_MARK`**（如 qc-ruleparser-fix2-2026-07-26）；部署后务必 `curl` 内网 `http://lab-management-282724-9-1408547492.sh.run.tcloudbase.com/api/v1/_diag/build` 核对标记是否更新 —— 标记旧=部署没生效/流量未切，**绝不能用"任务被清理"代替"确认成功"**。
- 公网域名 `lab-management.tcloudbaseapp.com` 常被 CDN 418 拦截；内网 host 直连才可靠。
- broken pipe 等推送中断=需重试整轮部署，否则线上代码与模型/列不一致→500。
