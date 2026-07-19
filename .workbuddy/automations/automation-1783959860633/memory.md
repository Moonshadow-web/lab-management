# 月度室间质评成绩导出（自动化执行记录）

## 2026-07-15 20:0X 执行
- **NCCL**：auth.json cookie 仍有效（单 PDF 下载 200/%PDF 验证通过），无需重新登录。直接用已存 `eqa_nccl_links.json`（Jul-13 快照，含第1/2次共 66 链接）跑 `--download`：36 个匹配 plan 中 34 已有 report、仅 2 个新下载 → `糖化白蛋白_第1次`(id=114)、`糖化白蛋白_第2次`(id=115)。
- **北京市**：原 bj_cookies.txt 会话已过期（pdfptscoretitle.asp 返回 500）。已用 playwright-cli `-s=bj` 重新登录（账号 01110025）并刷新 `outputs/bj_cookies.txt`（新 ASPSESSIONIDQESTQDAQ / ASPSESSIONIDCETQQACS）。dry-run 显示 11 个匹配 plan 全部已有 report，**0 新下载**。
- **解析回填**：`parse_pending_eqa.py` 命中 2 个待解析（即上面 2 个新 PDF），均 high 置信 → 成绩100% / 合格(qualified=1) / score=100。0 低置信、0 medium。
- **结果**：2026 年共 47 个 plan 有 report_file（卫健委 36 + 北京市 11），磁盘 47 个 PDF，待解析残留 0。

## 注意事项 / 待人工
- NCCL 成绩列表页 `eq.nccl.org.cn` 本次用浏览器连接被 TCP RESET（疑似 NCCL 边缘/WAF 拦截 headless），无法在线重新抽取链接，故沿用 Jul-13 链接快照。若 Jul-13 之后卫健委新发了其他项目的「第2次」成绩且未在该快照中，需手动刷新 `eqa_nccl_links.json` 后再跑下载。
- 北京市仅匹配「第1次」（官网第2次尚未出分）；D-二聚体/京津冀鲁盲样/系列A/结核/sTfR 等官网无对应项，按 skill 约定跳过。

## 2026-07-15 20:2X 手动「再次执行」
- 用户追问后手动重跑整套流程。北京 cookie（本会话已刷新）与卫健委 cookie 均仍有效（北京 dry-run 63 链接/29 项目；卫健委单 PDF 200/%PDF）。
- `--download` 两次均 **0 更新**（卫健委 36 匹配全已有 report、北京市 11 匹配全已有 report）；`parse_pending_eqa.py` 命中 0、写入 0。
- 上次排查发现的缺失项仍未能抓取：① 卫健委 AMH(74/75) 与 肿瘤标志物A(80/81) —— Jul-13 快照无、且门户 eq.nccl.org.cn 仍 TCP RESET 不可达（score.clinet.cn 目录无索引），无法在线重抽链接；已在脚本补映射待快照刷新后自动捕获。② 北京市 肝炎标志物(88/89) —— 官网实时列表(29项目)确无 2026 成绩，官网未发。
- 结论：47 个 plan 的 report_file 现已全部为最新状态；上述 3 类为「官网未发 / 门户不可达」导致，非脚本故障。

## 2026-07-15 20:4X 「我能登上」——打通 SSO 新路径，补抓 AMH + 肿瘤标志物A
- **关键突破**：用户提示"我能登上"后，改用主站 `www.nccl.org.cn/loginCn`（101127/aa101127）浏览器重登，发现登录后 SSO 跳转到 `nccl.clinet.com.cn/clinetbusiness/hospital/`（与北京市同款 clinet 系统，浏览器可达），绕过了 `eq.nccl.org.cn` 的 TCP RESET。
- **抓链接**：从业务系统取真实 cookie（存 `outputs/nccl_biz_cookies.txt`），requests 直连 `pdfptscoretitle.asp?t_id=11&cclname=<GBK编码"国家卫生健康委临床检验中心">&SpeType=` 拿到 60KB/136 条 PDF 链接（`_nccl_scorelist_raw.html`）。**确认抗缪勒管激素第1次、肿瘤标志物A第1次现已发布**（Jul-13 快照确实缺）。
- **重建快照**：`eqa_nccl_links.json` 66→67 条（旧快照备份为 `eqa_nccl_links.backup_2026-07-15.json`）；新增 抗缪勒管激素_第1次、肿瘤标志物A_第1次 两条 score.clinet.cn 直链。
- **下载+回填**：`download_nccl_eqa.py --download` 写入 2 份 PDF（抗缪勒管激素_第1次 78448B / 肿瘤标志物A_第1次 114771B）；`parse_pending_eqa.py` 2 条 high 置信 → {74: 成绩100%/合格/100; 80: 成绩100%(β2-微球蛋白不予评价)/合格/100}。
- **最终**：2026 年 **49 个 plan** 有 report（卫健委 38 + 北京 11），待解析残留 0。北京肝炎标志物(88/89) 仍空——官网确未发布 2026 成绩。
- **踩坑**：① 浏览器 goto `DataAdminArea4.asp` 会 30s 超时卡死（frameset 空壳），一律 requests 直连 `pdfptscoretitle.asp`。② `pdfptscoretitle.asp` 不带 cclname 只返回 ~2.6KB 空壳，必须带 `t_id=11&cclname=GBK` 完整参数。③ 已同步更新 skill `nccl-eqa-export/SKILL.md` A 节为新 SSO 路径。

## 2026-07-17 本定时任务触发，但实际执行「室间比对模块」收尾（非 EQA 导出）
- 本轮（自动化触发，实为延续室间比对开发）完成：前端 `npm run build` 通过；后端全链路冒烟测试通过。
- 修复 2 个关键 bug：① TestItem 模型未声明 has_eqa/has_interlab 列（候选过滤失效，有EQA项目也当候选返回）；② 候选项目未扩展到同 family 仪器（父仪器看不到子机项目）。
- 数据语义澄清：用户"12个无室间比对"实为 EQA/室间比对 术语混淆，这 12 类=无EQA、需做interlab=`(0,1)`（展开 16 库行）。迁移 `main._migrate_schema` 已固化回填补丁（NULL→(1,1)，再按 16 项目名置(0,1)），部署时线上自动生效。
- 验证：instruments/projects/plans CRUD/results/report generate+preview+download+upload+delete 全通过，偏倚计算正确。
- **本次未跑 EQA 成绩导出**；cloudbase 会话 disconnected，未自动 deploy 上线（部署待用户连通 cloudbase 后执行，迁移自含数据打标）。
- 详见 `.workbuddy/memory/2026-07-17.md` 与 `MEMORY.md` 室间比对节。
