# 自动化执行记录：NCCL/北京 EQA 成绩自动下载关联

## 2026-09-15 21:31 运行
- 登录态：NCCL（nccl_eqa_download.js 内登录）成功；北京 bj_login.js 点击超时导出无效 cookie（500），改用 bj_login_retry.js（form.submit）成功（9 cookies）。
- NCCL：刷新链接快照 90→93 条，新增「尿液定量生化第2次」「脑脊液生化检测第2次」——**本地/线上均无这两项第2次 plan 行，无法关联（已报告用户）**；48 个 NCCL plan 全部已有 report_file，0 新增。
- 北京：dry-run 发现官网第2次已出分（43 链接）但脚本硬编码只匹配第1次 → 修正 download_bj_eqa.py 按 (code,times) 匹配任意轮次；下载合并 11 份第2次报告入库；parse_pending_eqa.py 全部 high 置信回填（score=100，合格）；线上推送 10 份（47/53 已在线上）成功。
- 特殊处理：内分泌(85) 结果表 PDF 致线上端点 500（root cause: result 超长超 MySQL 列宽/该结果表解析崩溃）→ 该 plan 只用汇总表 + 短 result「合格（各子项详见报告）」上传成功，本地同步。
- 线上最终：2026 年 114 plan，69 有报告，0 遗留待解析。失败项：纤维蛋白(原)降解产物检测第1次下载 ECONNRESET（该 plan 本就有报告，无影响）。
- skill 已更新：北京轮次匹配新规 + 线上 500 两个根因 + bj_login form.submit 要点。

## 2026-10-01 20:10 运行（Oct双月首跑）
- 登录态刷新：NCCL 用 `make_nccl_auth.js`（Playwright）重写 `auth.json`（含 .clinet.com.cn cookie），实测 `score.clinet.cn` 的 PDF 直连下载 200/有效 PDF（无需单独建 score 域 cookie）。北京用 `bj_login_retry.js` 重写 `bj_cookies.txt`（6 cookies），之前 500 即 cookie 失效所致，刷新后 live list 正常（115 链接/55 项目）。
- ⚠️ NCCL 链接快照坑：`make_nccl_auth.js` 提取链接为 **0**（默认页只显当年、未注入 sltyear）。改走 `nccl_year.js 2026` 注入 sltyear+mysearch() 拿到 107 条（rounds 1=71/2=36，无第3次），备份旧 `eqa_nccl_links.json` 后覆盖为 `_2026` 版。**结论：每次跑务必用 nccl_year.js 刷快照，不要依赖 make_nccl_auth 的链接提取**。
- NCCL 下载（--download）：55 匹配、47 跳过（已有 report）、**5 新增** report_file → plan 20 凝血试验第2次 / 24 D-二聚体第2次 / 33 抗凝蛋白第2次 / 57 系列A第2次 / 113 FDP第2次。仅写 report_file+updated_at，`returned` 未动（39 不变）。
- 北京下载（--download）：live 匹配 23 全部已有 report → **0 新增**。跳过 8（常规化学A第2/3次、D-二聚体和FDP、京津冀鲁盲样、结核、sTfR —— 官网未发布该轮或不在映射）。
- 解析 `parse_pending_eqa.py`：5 total / **5 high / 0 medium / 0 low / 写回 5**。结果：20/24/57/113=成绩100%合格；33 抗凝蛋白=合格(定性，score空)。全库「report有成绩空」归零。
- **范围说明：本次仅写本地 data/app.db（生免速查工具本地库）。生产 CloudBase MySQL 不随本地改动上线，需另行 commit+push+部署 或 push_eqa_online 才反映。** 用户步骤未含上线，故未推送。
