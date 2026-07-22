# 项目长期记忆

## 项目基线
- 生化免疫专业组速查工具；栈 FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；8 模块；DB=CloudBase TDSQL-C MySQL（勿按 SQLite 思路排查）。
- 管理员 金子铮(id=2)，登录用户名 jinzizheng，线上密码 Jzz6827556；18 科室初始 123456 首登改密。

## 部署（铁律）
- 正确喂参：`(echo ""; sleep 3; echo "Y") | tcb cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force`
  - 第1提示「Enable gray deployment?」回车选默认 No(自动切换流量)；第2提示「取消并部署最新(Y/n)」喂 Y。旧 `printf 'Y\n'` 只答第1且误选灰度→流量不切换/部署不生效。
  - 构建源=origin/main（本地 commit 须先 push）；构建+切换 2-5min，`/_diag/build` 期间可能短暂空响应。就绪：`curl /api/v1/_diag/build` 返回 200。
- 公网 host 418=CDN 不转发，用内网 `lab-management-282724-9-1408547492.sh.run.tcloudbase.com`；勿反复 deploy（每次触发新 pod）。

## 登录/权限/前端铁律
- RBAC roles 逗号分隔；admin 通杀；会话 30min access+7d refresh，401 静默 refresh；禁用 Promise.all+静默 catch。
- 前端空白排查：先要 F12 Console 报错，勿臆测缓存/CDN。沙箱浏览器访问线上 host 被「风险提醒」拦截（curl 正常），故沙箱验证不可信。
- 权限 store 易错点：`auth.canWrite/canDelete/canAccessMenu` 用 `usePermissionStore()` 时 `let permStore` 须提到函数作用域，勿在 try 内 const 后块外引用（ReferenceError 炸白组件）。
- 仪器显示铁律：任何展示仪器处必须「名称(model)」，空型号仅名称；型号=Instrument.model。

## 业务模块约定
- EQA：/api/v1/eqa-plans；编号 年4+轮1+序1；北京机构 01110025/4731；肝炎/感染B/C 填 P/N+S/CO，快检仅 P/N。
- QC仪器：受控21台；替代：停用 AU5822(2)/DXI800C(3)/DXI800D(4)/DXI800急诊(6)/DXI800唐筛(7) → AU5821A(67)/AU5821B(68)/DXI800 1-4(69-72)/DXI800急(73)/唐(74)/AU5800急诊(5)。
- interlab：过滤 has_eqa=0 AND has_interlab=1；16例外→0，有EQA→0，其余→1；模板 定量019/定性018。
- comparison：/api/v1/comparison；分组1生化 67/68/5(参比68)，分组2 DXI800 69-74；DXI800 te=15% 不降(IL-6/BNP/cTnI/PCT/sTfR/IFA)，生化 CO2 te=10%；权威 WS/T 403—2024 字典在 services/comparison_report.py(键=系统代码大写)，新TE查字典勿写死；按水平 te_by_level/mode_by_level。
- qc_target：一批次一靶值；水平1/2/3；conventional/immediate；SI 界值 services/qc_target.py。
- 质量要求：三源同表 quality_requirements(wst403-2024/bj-hr-2025/nccl-2026)；GET /quality-requirements/_meta/matrix 综合比对视图；lookup_quality_goal 优先级 表cv>bjhr-cv>nccl-tea/3>json>字典>默认10%。
- QC月结/LJ：上传 LIS 时 _ensure_report_draft 生成5段模板落库；LJ 图项目+水平多选；已移除月小结Excel导出与质控图PDF。
- 文档预览：xlsx/xls 用 exceljs 转 HTML；docx mammoth；pdf 直接；后端补正确 media_type。

## 原始结果附件 + max_allowed_packet（重要）
- 字节存 MySQL BLOB（ComparisonAttachment/InterlabAttachment.data，LONGBLOB 16MB），不落磁盘。
- 上传图片经 services/attachment_compress.optimize_image_bytes 压缩（长边≤2400px、JPEG q85）；非图片原样；Pillow 缺失降级；超限 413。
- 预览/下载：get_current_user 支持 URL ?token=/cookie 兜底；前端 AttachmentPreview 内嵌预览。
- max_allowed_packet：单条 INSERT 受服务端限制（TDSQL-C 默认~4MB，超→上传500）。**该集群是 CloudBase 代管（集群名 cloudbase__SAmOhXfvyj，集群ID cynosdbmysql-l0kufcte），TDSQL-C 控制台入口被平台锁定，CloudBase 控制台也不暴露该内核参数 → 控制台路线走不通**。唯一可靠手段是代码侧：main.py 启动 SET GLOBAL 134217728 + dispose，且注册 SQLAlchemy `connect` 事件**每次新建连接自动 SET GLOBAL 134217728**，实例重启/连接池重建自愈。值须为1024倍数(134217728=128MB符合)。详见 2026-07-23 日志。

## 数据库与持久化
- 已弃 SQLite+CFS，用 CloudBase TDSQL-C MySQL：实例 cynosdbmysql-ins-102awksb，内网 10.0.1.18:3306，库 cloud1-0gjhamv53ff2298d；账号 labapp（外网按需开，平时关）；DATABASE_URL 在 cloudbaserc.json。
- 验证基线：schema/查询改动须面向 MySQL 验证；main.py 残留 PRAGMA/sqlite3 自愈代码已 try/except 包裹（MySQL 下跳过）；Base.metadata.create_all 自动建缺失表。

## 迁移原则（硬要求）
- 禁 DROP；新列 ADD COLUMN 幂等；老列 NOT NULL 用 ALTER COLUMN DROP NOT NULL 只放宽；诊断端点只 /build 免鉴权。

## CFS 历史（已弃用，仅留教训）
- 曾用 SQLite+CFS：malformed 自愈、挂载冲突(exit15)、部署连环故障(详见 7/19-20 日志)。现已切 MySQL 且控制台「存储挂载」关闭，永久不再需要 CFS。
