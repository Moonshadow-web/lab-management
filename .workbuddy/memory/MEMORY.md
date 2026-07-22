# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；8 模块；数据库已切 CloudBase TDSQL-C MySQL（见下方 #数据库与持久化，勿按 SQLite 思路排查）。
- 管理员 金子铮(id=2)，**登录用户名 jinzizheng**，线上密码 Jzz6827556；18 科室初始 123456 首登改密。

## 部署与数据
- 部署：`printf 'Y\n' | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`；构建源=origin/main（本地 commit 须先 push）；灰度 5-10min。
- **数据库已切 MySQL**（见下方 #数据库与持久化），不再依赖本地 SQLite 文件。`data/app.db` 仅作 Docker 镜像种子兜底（首次 MySQL 为空时回退）。
- 就绪验证：`curl /api/v1/_diag/build` 返回 200。
- **CDN 418**：公网 `lab-management.tcloudbaseapp.com` 418 = CDN 不转发。绕过用内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`。通常 CFS 挂载问题解决后自愈。
- **请勿反复 deploy**：每次 deploy 触发新 pod 创建；在 CFS 问题时期可能反复卡死。确认服务 normal 后再操作。

## 登录/权限/前端约定
- RBAC roles 逗号分隔；admin 通杀；会话 30min access+7d refresh，401 静默 refresh；禁用 Promise.all+静默 catch。
- **前端空白排查铁律**：先要用户贴 F12 Console 报错，再动手；不要臆测缓存/CDN/灰度。本沙箱 Playwright 访问线上 host 会被网络层「风险提醒」拦截页劫持（curl 同 URL 正常），故沙箱浏览器验证不可信。
- **权限 store 易错点**：`auth.canWrite/canDelete/canAccessMenu` 内若用 `usePermissionStore()`，声明必须提到函数作用域（`let permStore`），勿在 `try{}` 内用 `const` 声明后于块外引用（会 `ReferenceError: permStore is not defined` 炸白整个组件）。2026-07-21 因此 bug 导致 QC 月结/累靶整片空白。
- **仪器显示铁律（用户硬性要求 2026-07-22）**：**任何展示仪器的地方（下拉、表格、关联、报表、比对等）必须同时显示「名称 + 型号」**，仅显示名称会被误认。型号来源于 Instrument.model；前端展示格式统一 `名称(model)`，空型号时仅显示名称。涉及仪器选择/展示的组件改版时默认可加，勿省略型号。

## EQA
- 路由 /api/v1/eqa-plans；编号 年4+轮1+序1。北京临检机构 01110025/4731；肝炎/感染B/C 填 P/N+S/CO，快检仅 P/N。

## QC/仪器
- 受控仪器 21 台；替代关系：停用 AU5822(2)/DXI800C(3)/DXI800D(4)/DXI800急诊(6)/DXI800唐筛(7)；替代 AU5821A(67)/AU5821B(68)/DXI800 1-4(69-72)/DXI800急(73)/唐(74)/AU5800急诊(5)。

## 室间比对 interlab
- 过滤 has_eqa=0 AND has_interlab=1；三态：16例外→0、有EQA→0、其余→1。
- 16例外：HBsAg定量(83)/ST2(42)/抑制素B(67)/抗精子(88,89)/抗卵巢(90,91)/抗子宫内膜(92,93)/肺癌自身抗体(200)/17-羟(162)/17-酮(163)/NAG(211)/血氨(161)/ACE(101)/香草扁桃酸(164)；模板 定量019/定性018。

## 仪器间比对 comparison
- 路由 /api/v1/comparison；分组1生化 67/68/5(参比68)，分组2 DXI800 69-74。
- DXI800 用户偏好 te=15%(relative) 不降：IL-6/BNP/cTnI/PCT/sTfR/IFA。生化 group1 CO2 te=10%。
- 权威标准 WS/T 403—2024：te 语义=允许偏倚；字典 WST403_2024 在 backend/app/services/comparison_report.py（60 项，键=系统代码大写）。新 TE 直接查字典勿写死。校准修正：IgA8/IgM10/HBDH10；DXI 占位0.1→标准值；PREG 孕酮8/E2 10/β-HCG 10；血气 pH 0.015绝对/PCO2 4%/pO2 5%。
- 按水平细粒度：GroupItem.te_by_level/mode_by_level；_resolve_te/_resolve_mode 解析顺序 te_by_level>te>TE_LOOKUP。
- **代码坑（2026-07-19）**：comparison_report.py 内 **禁止定义同名函数覆盖**！曾因 `_parse_float` 定义两次（后者用 `re.search` 而本模块 `import re as _re`）导致 `_compute_bias`(定量报告必走) 抛 `NameError: name 're' is not defined` → 报告生成/预览 500（定性不崩）。字符串数值解析统一用 `_extract_float`（已含 `re`→`_re` 修正，可解析"5.2 mmol/L"带单位串）。

## qc_target
- 一批次一靶值；水平1/2/3；conventional/immediate；SI 界值 services/qc_target.py；生化多项仅存档。

## CFS 自愈/损坏恢复
- 现象 malformed；main._self_heal_db 自动：integrity ok直接用→REINDEX→dump重建→.lastgood 备份→镜像种子兜底。仅保留免鉴权 /_diag/build。
- 刷新镜像备份标准流程：临时加 admin 专用 GET /_diag/db（wal_checkpoint 后 FileResponse /app/data/app.db）→push→deploy→等切换→登录 curl 下载→杀本地遗留 uvicorn 清 wal/shm 锁→shutil.copyfile 覆盖 data/app.db→校验 integrity→移除端点再 deploy 等 /_diag/db 变 404。
- 实战教训：malformed 副本数据页仍可读；跨设备用 shutil.move；批量写走 engine.raw_connection 禁独立 connect；text() 只认命名参数；逐行 diff 勿只数行；interlab_items 不可恢复。

## 迁移原则（硬要求）
- 禁 DROP；新列 ADD COLUMN 幂等；老列 NOT NULL 用 ALTER COLUMN DROP NOT NULL（SQLite≥3.35）只放宽；绝不回退 DROP。诊断端点只 /build 免鉴权。

## 技术支持角色 technical_support
- 角色码在"级别"单选+ "角色"多选都出现；菜单仅 isTechnicalSupport 收口隐藏未授权模块；comparison/interlab 仅新建录入、edit 仅 admin/qc_manager；qc-monthly/qc-target member 可写不可删。本地测试号 jishuzhichi(id=20)。

## 爱康 LIS 导出格式
- GBK Tab 文本套 .xls；result→value，averageValue→target_mean，standardDeviation→target_sd，zValue 反算；itemName→test_item，batch→lot_no，testName→level，deviceId→instrument。代码 _read_rows+_COLUMN_ALIASES(提交19744f6)。
- **日期列 testDate** 常见格式 `2026-6-1 10:10`（月日非零填充），`_parse_date` 已兼容 `YYYY-M-D H:M` / `YYYY-M-D H:M:S` 及 `-/.` 分隔；原只支持零填充导致全部回退到每月 1 日（LJ 图全是 6-1）。

## QC 月结 / LJ 质控图（2026-07-19 改造）
- 文字报告：上传 LIS 数据时 `upload` 接口已调用 `_ensure_report_draft` → `draft_report` 自动生成 5 段模板文字并落库；前端可编辑、保存、预览、下载 Word。若 qc_summaries 为空则 `/report/docx` 业务 404「暂无月结数据」。
- **已移除**：月小结 Excel 导出（前端按钮+后端 `/export`）、质控图 PDF 上传/预览/删除（月小结展开行）。
- LJ 质控图：项目下拉 + 水平多选下拉（默认全选）；左侧表格按日期横向展示各水平测值+状态；底部「每日多水平状态汇总」（如 6-1 1水平 在控 2水平 在控）。

## Starlette 500
- 不返回 detail；已知 DB 错用 4xx+日志。

## 文档预览坑（2026-07-19 修复）
- 后端 documents.py preview 对 xlsx/xls media_type=None→部署环境回退 text/plain；前端 onPreview 原仅 docx(mammoth)/pdf 有渲染，xlsx/xls 走 previewBlob→window.open 当文本→乱码。
- 修复：前端用 exceljs(已装 ^4.4.0) 增加 xlsx/xls 分支转 HTML 表格（与 docx 一致），按文件头 PK→exceljs、OLE→提示下载、其余→gbk 文本；后端补 xlsx/xls 正确 media_type。

## 数据库与持久化（2026-07-20 全面变更）
- **已放弃 SQLite+CFS**，全面改用 **CloudBase TDSQL-C MySQL**（cynosdbmysql）。
- MySQL 实例：`cynosdbmysql-ins-102awksb`，内网 10.0.1.18:3306，数据库 `cloud1-0gjhamv53ff2298d`。
- 账号：`labapp`（密码同 admin；外网访问按需开关，平时关闭只用内网）。
- app 连接：cloudbaserc.json 中 `DATABASE_URL=mysql+pymysql://labapp:PASS@10.0.1.18:3306/cloud1-...`。
- 迁移方式：本地 pymysql 连接外网（临时打开）→ SQLAlchemy create_all 建表 → pymysql 逐行插数据 → 关闭外网 → deploy 切 MySQL DATABASE_URL。
- 数据备份：`online_backup.json`（391KB，38 条 QC 摘要 + 每日值），API dump → MySQL 恢复验证通过。
- **不再需要 CFS 持久卷**，cloudbaserc.json volumes 已清空，服务端「存储挂载」已关闭。
- **验证基线（重要）**：任何 schema/查询改动须面向 MySQL 验证，勿用 SQLite 内存库代替。main.py 启动逻辑里残留的 `PRAGMA`/`sqlite3` 自愈代码均被 `try/except` 包裹（MySQL 下报错即跳过，不中断启动）；`Base.metadata.create_all` 对 MySQL 执行即自动建缺失表。部署后 `/_diag/build` 标记切换即证明 MySQL 建表+启动成功。

## CFS 挂载冲突（平台级，非代码问题）
- **根因**：TCB CloudRun side-dns-cache 边车容器的 lifecycle hook 在宿主上执行 `/mount_cfs.sh`，挂载目标 `/mnt/cfs/10-0-1-2` 被本地磁盘 `/dev/vdb` 抢先挂载。
- **症状**：每次 deploy 新版本 pod 起不来（mount source mismatch, exit 15），公网 418；旧 pod 不受影响（内部 host 正常）。
- **工程师修复**：清宿主机 stale 挂载（非代码修复）；控制台「服务配置→存储挂载」关闭后永久不再需要 CFS。
- **工单沟通要点**：明确是 platform-level、不是 app volumes 配置；附上 DST_PATH + Pod 名 + exit 15 日志即可加速排查。

## 7/19-20 部署连环故障与修复
1. **upload 500**：`_lookup_qr_goal` 中 `name.contains(col)` AttributeError。11736ee → Py 侧过滤 + try-except。
2. **models/__init__.py 缺 import**：`__all__` 有 QualityRequirement 但没有 `from .quality_requirement import ...`。19d5bbe。
3. **Pydantic v2 `_file` 字段**：reagent_management.py `_file: UploadFile` 不兼容。c73e2f5 → 改为 `file`。
4. **SQLAlchemy mapper InvalidRequestError**：reagent_management.py 多张表的 FK 列只有 `Integer` 没有 `ForeignKey`。dbdae85 → 补全 6 处 FK。
5. **容器 DB 丢失**：无 CFS 时每次 deploy 覆盖种子库。切 MySQL 从根本上解决。

## 质量要求模块 (2026-07-19)
- 三源同表 quality_requirements，source 字段分：wst403-2024/bj-hr-2025/nccl-2026。
- **综合比对视图**：GET /quality-requirements/_meta/matrix；以 test_items(124项) 为行，三源为列；支持搜索+分页；模糊匹配兜底(name包含关系)。前端"综合比对"tab 为最左第一个 tab，默认进入。
- 原有三个标签页完整保留；seed 后矩阵数据才可见。

## QC 质量目标查找（2026-07-19 改造）
- `lookup_quality_goal(test_item, aliases, db)` 优先级：
  1. `QualityRequirement` 表：`wst403-2024.cv` > `bj-hr-2025.cv` > `nccl-2026.tea/3`
  2. 原有 `qc_quality_goals.json` 文件（兼容）
  3. `comparison_report.WST403_2024` 字典 TE/3（别名匹配英文代码）
  4. 默认 `"10%"`
- 匹配：item_name 精确→子串含→别名含逐级递进
- `_extract_first_pct(s)` 从复杂串（"靶值 ±20% 或 ±5μg/L"）提取首个%数值
