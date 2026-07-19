# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0+SQLite / Vue3+Vite+Element Plus+Pinia；8 模块。
- 管理员 金子铮(id=2)，线上密码 Jzz6827556；18 科室初始 123456 首登改密。

## 部署与数据
- 部署：`printf 'Y\n' | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`；构建源=origin/main（本地 commit 须先 push）；灰度 5-10min。
- 线上 DB 唯一源；本地 data/app.db 是种子/兜底库（gitignored，但 .dockerignore 不排除 → 进镜像备份）。
- 就绪验证 URL 返回 200。
- **CDN 418 排查**：公网 `lab-management.tcloudbaseapp.com` 返回 418 "X-Cache-Lookup: Return Directly" = CDN 不转发到后端。绕过用 TCB 内部 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`（从 `tcb logs search` 取）。容器 "normal" 但 CDN 缓存/规则异常时只能等 TCB 平台处理。

## 登录/权限/前端约定
- RBAC roles 逗号分隔；admin 通杀；会话 30min access+7d refresh，401 静默 refresh；禁用 Promise.all+静默 catch。

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

## Docker/CFS 硬约束
- 持久卷 mountPath=/app/data；构建期 /app/data 必须空，子目录运行时建；.dockerignore 排除 backend/data/；改后须 push+deploy。

## 上线必做（CFS 恢复后）
- 部署积压提交→清 AU5800(id=5) 重复月小结（走 API 删）→重生成 CZ-012 月结报告。

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
