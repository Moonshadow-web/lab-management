import os, time
from playwright.sync_api import sync_playwright

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile_shots")
os.makedirs(OUT, exist_ok=True)

def shot(pg, name):
    try:
        pg.screenshot(path=os.path.join(OUT, f"{name}.png"))
        print("shot", name)
    except Exception as e:
        print("FAIL", name, repr(e))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    )
    pg = ctx.new_page()
    pg.goto(BASE + "/login", wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)
    confirm = pg.locator("button:has-text('确定访问')")
    if confirm.count():
        confirm.first.click()
        pg.wait_for_timeout(2500)
    pg.wait_for_selector("input", state="visible", timeout=20000)
    pg.locator("input").first.fill("jinzizheng")
    pw = pg.locator("input[type=password]")
    if pw.count():
        pw.first.fill("Jzz6827556")
    else:
        pg.locator("input").nth(1).fill("Jzz6827556")
    pg.locator("button.el-button--primary").first.click()
    pg.wait_for_timeout(3000)

    # 进仪器档案列表
    pg.goto(BASE + "/instruments", wait_until="domcontentloaded")
    pg.wait_for_timeout(2500)
    shot(pg, "instruments-list")

    # 横向滚动表格容器到最右，使操作列的“档案”按钮进入视口
    pg.evaluate("() => { document.querySelectorAll('.table-wrap, .el-table__body-wrapper').forEach(w=>{ try{w.scrollLeft=w.scrollWidth;}catch(e){} }); }")
    pg.wait_for_timeout(800)

    btn = pg.locator(".el-table .el-button:has-text('档案')").first
    if btn.count():
        try:
            btn.click(force=True)
        except Exception as e:
            print("档案 click force fail", repr(e))
        pg.wait_for_timeout(1800)
        # DOM 检查：抽屉是否打开、宽度、描述列表每行 cell 数（单列=2，双列=4）
        info = pg.evaluate("""() => {
          const d = document.querySelector('.el-drawer');
          if(!d) return {has:false};
          const tbl = d.querySelector('.el-descriptions__table');
          const row = tbl ? tbl.querySelector('tr') : null;
          const cells = row ? row.children.length : 0;
          return {has:true, width: getComputedStyle(d).width, descCellsPerRow: cells};
        }""")
        print("DRAWER_INFO", info)
        shot(pg, "archive-drawer")
        # 滚到抽屉底部看表格区
        pg.evaluate("() => { const d=document.querySelector('.el-drawer__body'); if(d) d.scrollTo(0, d.scrollHeight); }")
        pg.wait_for_timeout(700)
        shot(pg, "archive-drawer-bottom")
        # 把描述列表单列效果再截一张（滚回顶部）
        pg.evaluate("() => { const d=document.querySelector('.el-drawer__body'); if(d) d.scrollTo(0,0); }")
        pg.wait_for_timeout(400)
        shot(pg, "archive-drawer-top")
    else:
        print("NO 档案 BUTTON")

    b.close()
print("ALL DONE")
