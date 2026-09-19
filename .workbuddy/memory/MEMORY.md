# 项目长期记忆（精简版 2026-09-19）

## 项目基线
- 生免速查工具：FastAPI+SQLAlchemy2.0 / Vue3+Vite+Element Plus+Pinia；DB=CloudBase TDSQL-C MySQL（非 SQLite）。
- 管理员 金子铮(id=2)：jinzizheng / Jzz6827556；18 科室初始 123456 首登改密。
- 专业组隔离：`get_current_group` + 路由 `group_scoped=True`。组字典 `models/lab_group.py::LAB_GROUPS` = sm 生化免疫 / lj 临检 / wsw 微生物 / fz 分子 / xk 血库。生免组 jinzizheng 看不到他组仪器；临检组 龚珂/gk123456；分子组 fz。跨组建档：管理员先 `POST /api/v1/auth/switch-group?group_code=<code>` 换 token 再建。

## 部署铁律
- **工具链路径会变，每次用前先 ls 核对**（2026-09-19 实测）：
  ```
  NODE="C:/Users/81526/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"     # 旧的 -2 目录已被删
  TCBJS="C:/Users/81526/.workbuddy/binaries/node/workspace/node_modules/@cloudbase/cli/bin/tcb"   # 在 workspace 下，不在 versions 下
  构建：cd frontend && "$NODE" node_modules/vite/bin/vite.js build --emptyOutDir false
  部署：(sleep 12; echo "Y"; sleep 10; echo "Y") | "$NODE" "$TCBJS" cloudrun deploy -e cloud1-0gjhamv53ff2298d -s lab-management --force
  ```
  ⚠️ **路径必须写 Windows 形式 `C:/...`**：node.exe 是 Windows 程序，Git Bash 的 `/c/Users/...` 会被解析成 `D:\c\Users\...` → `Error: Cannot find module`。**构建、部署都一样**（踩过）。
  ⚠️ 并发部署时 tcb 会交互式问 Y，漏喂/早喂会挂住 → `TaskStop` 后重跑；`git fetch/push` 需 SSH，**不能放后台**（前台 + dangerouslyDisableSandbox）。
- 内网 host `lab-management-282724-9-1408547492.sh.run.tcloudbase.com` 可直连（公网 418 是 CDN 不转发）。列表接口必带 `page_size`；登录 OAuth2 表单，token ~15 分钟过期，跨步脚本每次重新 login。
- **本地修复 ≠ 上线**：必须 commit+push 后部署，部署前 `git log -S <关键函数>` 确认已提交。`git push` 不要放后台（沙箱拒读 `~/.ssh`）；需前台 + `dangerouslyDisableSandbox=true`。
- **`_BUILD_MARK` 不可信**：并发会话会互相改写 `diag.py` 的标记，且对方的部署会用他本地 dist 覆盖我的 dist。唯一可靠验证（三级全中）：① curl `/` 取入口 `index-<hash>.js` ② 从入口 chunk grep 目标页面 chunk 名 ③ curl 该 chunk grep 本次新增的中文关键字。不中 → 重跑部署。另可核对线上 `index.html` 入口 hash == 本机 `frontend/dist/index.html`。
- 无持久卷：容器 `/app/data` 重建即清空，上传文件持久化靠 `cos_storage` 双写（bucket `636c-cloud1-0gjhamv53ff2298d-1408547492` / ap-shanghai）；本地 `cos_storage.ready=False` 属正常降级。
- 前端：`Dockerfile` 直接 `COPY frontend/dist`（gitignore）→ `vite build --emptyOutDir false` + `git add -f frontend/dist` + 推 + 部署。
- 部署前必 `import app.main` 冒烟（py_compile 不足）。部署报 `ENOENT .../outputs/reportgen/html/*.html` = 别的会话在生成报告，等 30-60s 重试。
- 多 AI 并发改同一项目时按模块错开，或约定「谁部署谁最后验」。

## 血泪坑（勿重犯）
- **security.py 是禁区**：勿加新函数/类（曾致容器连崩 4 次）；复用认证逻辑放 `core/_auth_helpers.py`。
- **新增模型列先查 import**（`Float`/`JSON` 等未在 `from sqlalchemy import (...)` 里 → NameError → 容器崩溃循环）。本地无 sqlalchemy，用 AST 扫描类型名是否已 import。
- **静默 `except Exception: pass` 会掩盖 NameError/ImportError**（曾致 `documents.py` 漏 `import json` → 显式关联两年不生效）。排查时优先加诊断端点把异常打出来。
- **批量写入接口与单条接口必须共用同一套自动填充逻辑**（`_generate` 漏自动关联 → 95 条数据缺列）。
- **json_fields 经 ORM 整列丢失**：crud_base 的 `_serialize`+`_to_read` 是绕过方案，勿删。
- API 路径带 router 前缀（`/api/v1/...`）；404/405 先 curl `/openapi.json`，别被 SPA fallback 误导。
- 前端跳登录 = 拦截器 401 → gotoLogin，业务层 try/catch 无效；修法是登录后回跳 `?redirect=`。
- **QCList template ref**：`el-tab-pane` v-for + 内嵌 `template v-if` → ref 是数组且 `r[0]` 属隐藏 pane；取元素必须 `list.find(el => el.offsetParent !== null)`。动态 `import('echarts')` 必带 `.catch`；init 后挂 ResizeObserver+rAF resize。
- **Vue 取 DOM ref 前必须先让 `v-if` 成立**（`AttachmentPreview.vue` 教训）：分支内先 `loading.value=false`，再 `nextTick`+轮询等挂载。
- **Git Bash 里禁止裸 `python`**：会命中 Windows Store 存根并静默挂起。一律用绝对路径（见下）。
- git 索引锁（Win）：`GIT_INDEX_FILE=.git/alt_index` plumbing 绕过，锁释后 `git reset --mixed HEAD`。
- **UI 自动化不可靠**：`/verification` 页签 Playwright 点击后 DOM 已切但内容不刷新 → 涉及该页签的断言改以 API 结果为准。

## 业务模块要点
- **项目说明书归属靠「项目名+别名」匹配**（`documents.py::project_manuals`）→ 别名混入别的项目名会挂错；别名要覆盖标题可能写法（C3 需「补体C3c」）。现返回 `linked_projects` 数组（显式 `manual_doc_ids` 关联可多项目，自动匹配仍唯一）；诊断端点 `GET /documents/_diag/manual-link?doc_id=NNN`。
- **德赛特定蛋白证件号**：仪器 `苏械注准20222221910/国械注进20152221623`；试剂 ASO 20152402319、RF 20152402224、IgG 20152402033、IgM 20152402010、IgA 20152402039、C3c 20152402027、C4 20152402051；校准品 ASO 20152402032、RF 20152402041、特定蛋白 20152402053。说明书源目录 `D:\民航总医院\生免组管理体系文件\生免试剂说明书\德赛说明书`。
- **性能验证报告导入**：`POST /api/v1/report-archives/upload`（multipart）→ `services/vrf_parser.py::parse_and_store` 解析（`主封面` R20-36 偶数行 E 列 + `结果汇总` sheet）→ 建 `verification_reports` + `report_archives`。解析器只依赖 openpyxl，**可本地 `sys.path.insert(0,'backend')` 预演**；上传后再用 API 逐字段比对。上传时显式传对 `report_type`。改解析器后用 `POST /report-archives/{aid}/reparse` 刷新历史记录。
- **「是否申请认可」判定**：`verification_reports.py::_is_cnas` 从 `accredited_scopes` 动态加载，经 `_norm_project_name` 归一化后做边缘+修饰词匹配，`_CNAS_ALIAS_PAIRS` 兜底；新增认可项目无需改代码，项目名差异大时补别名。
- **能力范围表 perf_* 填厂家说明书值时必须标注来源**，否则被当成室验证数据。
- **测量不确定度 `u_cal` = 标准不确定度 u（k=1）**：`u_c=√(u_rw²+ucal²+bias_rms²)`，`U=2×u_c`。证书给「U=2%, k=2」应填 1.0。
- **test_items「试剂」=「品牌」(brand)**，不单存 reagent 列、前端不展示试剂列。
- EQA：北京 01110025/4731；**单位换算豁免**：骨代谢组(id110/111) PTH/VD 不换算（`eqa.py::_no_convert_unit_for` + 前端 `QCList.vue::matchConv`，前后端同步维护）。
- comparison 权威字典 WS/T 403—2024（`services/comparison_report.py`）。
- Westgard 月结：R-4s 相邻对按本水平靶值归一化判 |z差|>4；已失控点冻结；上传规则列覆盖后端，严重度 1-3S>2-2S>R-4S>10-x>1-2S。
- 文档预览：xlsx exceljs / docx mammoth / pdf 直；旧 .doc(OLE2) 按文件头判定。
- 排班 scheduling：四表 Post/Plan/Assignment/Config；夜班不自动生成；发热白班固定人每 4 工作日一班。
- 提醒推送：站内+邮件+ServerChan 三路，SendKey 存 wx_uid，每天 08:00 聚合 1 条。
- 试剂配送角色：仅「到货接收」，只能改自己创建的单，到货确认才入库。
- 人员继教 education：PersonnelMaster+5 子表+附件(COS)，`scripts/import_personnel_full.py`，共 90 条。培训签到表 BG-SM-PX-006（页脚「BG-SM-PX-006 检验科生化免疫组 生效日期：2026.9.1」，名单按姓名去重）。`training_session` 有 3 个自动解析列（exam_person_count/exam_pass_rate/eval_satisfy_rate）。
- 15189 认可能力范围：第 4 个 15189 tab，`POST /accredited-scope/batch?replace=true` 种子，更新用 PUT，导入 64 条。
- **维修二维码**：免登录链接 `…/repair-fill?code=<dept_no>`；公开端点 `/api/v1/public/repairs/by-code/{code}`，后端按 `dept_no` 取 `first()` → 同编号多台会串台，建档前查重。脚本 `scripts/gen_repair_qr_pdf.mjs`（生免）/ `gen_repair_qr_pdf_lj.mjs`（临检），A4 2×3 六联。

## 工具链经验
- **本机 Python**：一律用绝对路径 `C:/Users/81526/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（managed venv）。**该环境已装 python-docx、htmldocx、bs4、lxml、httpx、PIL、click**（旧记忆说"managed 3.13 没有 docx"已过时）。
- **HTML→DOCX（tencent-docx 插件）Windows 实测**：官方 `scripts/wb/local/setup-html-to-docx.sh` 是 Linux 向的（检查 `venv/bin/python`，Windows uv 建的是 `Scripts/python.exe`），且 `uv pip install` 会挂满 4 分钟被杀 → **别用它**。
  直接用托管 venv：
  `cd <plugin>/skills/html-to-docx/scripts && <managed python> -m html_to_docx convert in.html -o out.docx`
- **docx 页数核验**：PowerShell COM 开 Word 转 PDF（DisplayAlerts=0、只读）→ pypdf 数页；Word COM 无 stdout，结果经文件带出。
- **扫描件 PDF 无文字层**：无 OCR 环境，别装 rapidocr；用 pillow+pypdf `page.images` 提图缩放 ~1400px → Read 多模态读图。
- 软著源码 docx 正好 60 页参数：代码 7.5pt Consolas、页眉 8pt、边距 1.5cm、行距 1.0、末页不加分页符。
- 问卷星→培训附件：`wjx response query --vid` 取答卷，`POST /api/v1/education-attachments/{owner_type}/{owner_id}?kind=exam|effect_eval`（files 多文件）；模板 `outputs/wjx/{aggregate.js, gen_docx.js}`，Node docx@9.6.1。
- 文件清单编号改造（2026-09-19）：`BG-SM-GL-000-生化免疫组文件清单.docx` 内 `MHZYY-SM-SOP-xxx` → `MHZYY-JYK-SM-SOP-xxx`（仅插前缀、序号不变），改 22 条；**勿动** `BG-SM-CZ`(66)/`BG-SM-GL`(17)/`BG-SM-PX`(5)。run 级替换保格式，备份 .bak-20260919。
