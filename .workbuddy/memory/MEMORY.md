# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 思路排查）。
- 管理员 金子铮(id=2)，登录 jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。

## 部署（铁律）
- 喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`
  - 第1提示回车选默认 No(自动切流量)；第2提示喂 Y。旧 `printf 'Y\n'` 误选灰度→流量不切换。
  - 构建源=origin/main（先 push）；就绪看 `curl /api/v1/_diag/build` 返回 200。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；公网 418=CDN不转发；勿反复 deploy（每次新 pod）。
- **部署状态判断**：CLI 报「状态异常/无法发布/不存在灰度」等**不等于真的卡死**（详见文末「卡死的灰度发布」更正）。部署是否真生效，只以 `/api/v1/_diag/build` 的 `_BUILD_MARK` 为准；标记未更新时**先问用户去 Cloud 控制台核对真实情况**，不要自作主张让用户手动取消灰度。

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
- **文件存储 = MySQL LONGBLOB（根治部署丢文件）**：文档字节原写 `LocalStorageBackend(UPLOAD_ROOT)` 容器本地盘，每次 `tcb cloudrun deploy` 换容器即丢 → 预览/下载 404。2026-07-29 已改为文档字节入库 MySQL `documents.data`/`document_versions.data`（`LargeBinary(16MB)`=LONGBLOB），上传/新版本写 DB、预览下载优先读 DB、磁盘仅兜底（与 ComparisonAttachment/InterlabAttachment 一致）。`database.py` 引擎 connect 事件全局 `SET SESSION net_write_timeout=28800`（CloudBase 代理默认 60s 会掐大 BLOB 写入，根因已定位）。迁移端点 `_backfill_data_from_disk`（admin，幂等）已跑：documents 全固化(483/483，written=0/skipped=483)，document_versions 286 条迁入、failed=0。仅**早期(pre-修复)上传、字节已随旧容器丢失**的 ~12 个文档需重传（doc 503 BG-SM-PX-005 / 504 / 506 / 236 / 163 / 502 / 505 / 394 / 395 / 396 / 397 / 399；另 14 条是 file_path 空记录非丢失）。CFS 持久卷早因 bug 弃用，数据全在 CloudBase MySQL（勿再按 CFS/本地盘理解）。
- **上传文件内容/扩展名错配**：用户常把旧版 Word(.doc, OLE2 头 D0CF11E0) 存成 .docx 名上传 → 预览进 mammoth/JSZip 报「Can't find end of central directory」。前端 `onPreview` 已改为按文件头字节判定真实格式，旧版 .doc 显示清晰提示（下载用 Word/WPS 打开，或另存为 .docx 重传）。上传时若想自动纠正扩展名可加 OLE2 检测（尚未实现）。

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
- **前端产物必须强提交进 git 才能上线（关键 gotcha）**：`Dockerfile` 直接 `COPY frontend/dist ./frontend/dist`，**云端不重构建前端**；而 `frontend/dist/` 在 `.gitignore` 中 → 若只 `git add` 前端源码，dist 不会被纳入，部署后线上仍是旧前端。修法：本地 `node_modules/vite/bin/vite.js build` → `git add -f frontend/dist` → 提交推送 → 部署。核对前端是否上线：探测内网静态资源（如 `/assets/Dashboard-<hash>.js` 返回 200，旧 hash 返回 404），比轮询 build 标记更准。
- **多 AI 并发改 origin/main + 改 `diag._BUILD_MARK` 会互相覆盖**：某 AI 提交可能把标记改成自己的值并顶掉别人的推送。应对：部署前 `git fetch` 核对真实远端，确认自己的提交在 tip；若被覆盖，重设 `_BUILD_MARK` 为本轮值、强提交 dist、再 deploy（CLI 提示有并发任务时输 Y 取消并部署最新）。

## ⚠️ 重要更正：所谓「卡死的灰度发布」并不存在（2026-07-26 用户澄清）
- **过去我曾误判存在「卡死的灰度发布 / 状态异常无法发布」阻塞流量切换**。用户明确澄清：**这个问题实际上不存在**。CLI 的 `promote`/`rollback`/`setTraffic` 报错（如「状态异常，无法发布」「不存在灰度中的版本」）并不代表真的卡死，可能是我对 CLI 行为/部署状态理解有误。
- **正确做法**：当部署疑似「未生效/流量未切」时，**不要自己下「灰度卡死」的结论**，也**不要据此让用户去控制台手动取消灰度**。应**直接问用户**，并**等用户去 Cloud 控制台查看真实部署情况**（版本/流量/构建状态）后，根据用户的反馈再判断。
- 唯一可靠的「部署是否生效」判据仍是：`curl` 内网 `/api/v1/_diag/build` 看 `_BUILD_MARK` 是否更新。若标记没变，先和用户确认真实情况，再决定下一步，而非假定灰度机制故障。

## 试剂配送角色（reagent_delivery，2026-07-27 新增）
- 角色定位：仅「到货接收」界面有权限；只能新建/修改**自己创建**的收货单；**不能删除**、不能改他人记录；**看不到工作台**。
- 落地方式（非新增数值级别字段，沿用现有 roles 逗号串+模块权限表）：
  - `module_permission.py` 新增模块 `reagent-receivings`（默认 admin/reagent_manager/reagent_delivery）；`reagents` 模块仍仅 admin/reagent_manager，故试剂配送拿不到试剂管理其余页。
  - `security.py ROLE_LABELS`、`users.py ROLE_OPTIONS`、`module_permission.py ALL_ROLES/ALL_MODULES` 均加「试剂配送/reagent_delivery」。
  - 前端 `auth.js`：`canAccessMenu` 对 `reagent_delivery` 同 `technical_support` 严格按授权收口；`AppLayout.vue` 加独立「到货接收」菜单(moduleKey reagent-receivings) 并隐藏工作台；`router` 阻断试剂配送访问 `/dashboard`。
- 到货接收已改为**确认后才入库**：`create_receiving` 不再写 ReagentStock；`POST /receivings/{id}/confirm` 才累加库存并记 is_confirmed/confirmed_by/confirmed_at；旧记录(is_confirmed NULL)迁移时回填=1（已入库视为已确认）。`Receiving.created_by` 记创建人，用于「仅改自己」收口。
