import os, time
from playwright.sync_api import sync_playwright

BASE = "https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile_shots")
os.makedirs(OUT, exist_ok=True)

routes = {
    "dashboard": "/dashboard",
    "test-items": "/test-items",
    "documents": "/documents",
    "instruments": "/instruments",
    "qc": "/qc",
    "reagents": "/reagents",
    "training": "/training",
    "verification": "/verification",
    "iso15189": "/iso15189",
}

def shot(pg, name, full=False):
    try:
        pg.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
        print("shot", name, "(full)" if full else "")
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
    # 登录页先截一张（看登录页本身是否反人类）
    pg.goto(BASE + "/login", wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)
    # 处理 CloudBase 测试域名访问提示（如“确定访问 (2s)”）
    confirm = pg.locator("button:has-text('确定访问')")
    if confirm.count():
        confirm.first.click()
        pg.wait_for_timeout(2500)
    shot(pg, "00-login")
    # 登录
    pg.wait_for_selector("input", state="visible", timeout=20000)
    pg.locator("input").first.fill("jinzizheng")
    pw = pg.locator("input[type=password]")
    if pw.count():
        pw.first.fill("Jzz6827556")
    else:
        pg.locator("input").nth(1).fill("Jzz6827556")
    pg.locator("button.el-button--primary").first.click()
    pg.wait_for_timeout(3000)

    for name, r in routes.items():
        try:
            pg.goto(BASE + r, wait_until="domcontentloaded")
            pg.wait_for_timeout(1800)
            shot(pg, name)
        except Exception as e:
            print("NAV FAIL", name, repr(e))

    # 编辑弹窗（项目查询卡片里点“编辑”）
    try:
        pg.goto(BASE + "/test-items", wait_until="domcontentloaded")
        pg.wait_for_timeout(1800)
        edit_btn = pg.locator(".header-actions button:has-text('编辑')").first
        if edit_btn.count():
            edit_btn.click()
            pg.wait_for_timeout(1500)
            shot(pg, "edit-dialog")
        else:
            print("EDIT SKIP: no edit button")
    except Exception as e:
        print("EDIT FAIL", repr(e))

    b.close()
print("ALL DONE")
