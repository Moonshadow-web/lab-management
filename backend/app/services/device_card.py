# -*- coding: utf-8 -*-
"""设备卡片（仪器标识卡 + 维修二维码）生成服务

输出：PDF（ReportLab 精确绘制，版式与网页预览 1:1 对应）
版式：A4 竖版，**每页 3 张卡片**（打印后沿卡片外框裁剪）
     卡片宽 9.21cm，10 行；标签列 3.50cm，值列 3.30cm，二维码列 2.41cm

要素来源（仪器档案）：
    设备编号 dept_no / 设备名称 name / 厂家型号 model / 设备状态 status
    设备负责人 owner / 开始使用日期 start_date / 本次校准、下次校准（CalibrationRecord）
    设备维修联系方式 repair_contact（默认 3000，允许修改）
"""
import io
import os
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ---------- 颜色 / 尺寸 ----------
C_TITLE_BG = HexColor("#5a6270")   # 深灰蓝标题栏
C_LINE = HexColor("#333333")       # 表格线
C_TEXT = HexColor("#111111")

CARD_W = 9.21 * cm
COL_LABEL = 3.50 * cm
COL_VALUE = 3.30 * cm
COL_QR = 2.41 * cm                 # 3.50 + 3.30 + 2.41 = 9.21cm
ROW_H = 0.62 * cm
TITLE_H = 0.72 * cm
TOP_ROWS = 5                       # 二维码占前 5 行
PER_PAGE = 3                       # 每页 3 张
GAP = 0.45 * cm

_FONT = None
_FONT_BOLD = None


def _ensure_font():
    """注册中文字体（容器内可能没中文字体，多路径尝试）"""
    global _FONT, _FONT_BOLD
    if _FONT:
        return
    candidates = [
        (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simhei.ttf"),
        (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"),
        (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyh.ttc"),
        ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
         "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ("/usr/share/fonts/truetype/arphic/uming.ttc",
         "/usr/share/fonts/truetype/arphic/uming.ttc"),
    ]
    for reg, bold in candidates:
        try:
            if not os.path.exists(reg):
                continue
            pdfmetrics.registerFont(TTFont("CardCN", reg))
            bold_src = bold if os.path.exists(bold) else reg
            try:
                pdfmetrics.registerFont(TTFont("CardCN-Bold", bold_src))
            except Exception:
                pdfmetrics.registerFont(TTFont("CardCN-Bold", reg))
            _FONT = "CardCN"
            _FONT_BOLD = "CardCN-Bold"
            return
        except Exception:
            continue
    _FONT = "Helvetica"
    _FONT_BOLD = "Helvetica-Bold"


def font_ok() -> bool:
    """是否成功加载了中文字体（False = 会渲染成方块，必须阻止出卡）"""
    _ensure_font()
    return _FONT not in ("Helvetica", "Helvetica-Bold")


def ym(v: str) -> str:
    """把各种日期写法归一成「YYYY 年 M 月」（卡片只显示到年月，不显示具体日子）"""
    if not v:
        return ''
    s = str(v).strip()
    m = re.search(r'(\d{4})\s*[-/年.]\s*(\d{1,2})', s)
    if m:
        return f'{m.group(1)} 年 {int(m.group(2))} 月'
    m = re.search(r'(\d{4})', s)
    return f'{m.group(1)} 年' if m else s


def _make_qr_png(url: str, path: str):
    """生成二维码 PNG；失败返回 None（卡片仍可生成，只是无图）

    ⚠️ 缓存 key 必须用「完整 URL」，不能只用仪器编号 ——
    否则 http 时代生成的旧 PNG 会被复用，导致改 https 后二维码还是旧的。
    """
    if os.path.exists(path):
        return path
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except Exception:
        return None
    try:
        qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=24, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image(fill_color='black', back_color='white').convert('RGB').save(path)
        return path
    except Exception:
        return None


def _text(c, x, y, txt, size, font=None, color=C_TEXT):
    if txt in (None, ""):
        return
    c.setFont(font or _FONT, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, str(txt))


def _status_text(status: str, size: float):
    """状态行：(items, total_width, em)
    宽度按实际字号估算：框 0.75em + 文字 2 字(1.2em) + 间隔 0.9em
    """
    opts = (('在用', '在用'), ('维修', '维修'), ('停用', '停用'))
    parts = [(label, status == val) for label, val in opts]
    em = size
    box = 0.80 * em
    text_w = 1.35 * em          # 2 个汉字
    gap = 1.15 * em             # 项间距，明显留空
    pad = 0.18 * em             # 框与文字间距
    item_w = box + pad + text_w + gap
    return parts, item_w * len(parts), em, box, gap, pad


def _draw_status(c, cx, cy, status, size):
    """在 (cx, cy) 处居中绘制「□在用 □维修 □停用」状态行（矢量勾选框）"""
    parts, total, em, box, gap, pad = _status_text(status, size)
    x = cx - total / 2
    c.setStrokeColor(C_TEXT)
    c.setFillColor(C_TEXT)
    for label, on in parts:
        c.setLineWidth(0.9)
        c.rect(x, cy - box * 0.32, box, box, stroke=1, fill=0)
        if on:
            c.setLineWidth(1.3)
            c.line(x + box * 0.24, cy + box * 0.22, x + box * 0.44, cy - box * 0.06)
            c.line(x + box * 0.44, cy - box * 0.06, x + box * 0.78, cy + box * 0.42)
        c.setFont(_FONT, size)
        c.drawString(x + box + pad, cy, label)
        x += box + pad + 1.35 * em + gap


def _draw_card(c, x0, y_top, item, qr_dir, host):
    """画一张卡片。x0,y_top = 卡片左上角"""
    _ensure_font()
    code = (item.get('dept_no') or '').strip()
    name = (item.get('name') or '').strip()
    model = (item.get('model') or '').strip()
    status = (item.get('status') or '在用').strip()
    owner = (item.get('owner') or '').strip()
    start = ym(item.get('start_date'))
    cal = ym(item.get('cal_date'))
    nextcal = ym(item.get('next_cal_date'))
    contact = (item.get('repair_contact') or '3000').strip()

    # ---- 标题栏 ----
    c.setFillColor(C_TITLE_BG)
    c.rect(x0, y_top - TITLE_H, CARD_W, TITLE_H, stroke=0, fill=1)
    _text(c, x0 + CARD_W / 2, y_top - TITLE_H / 2 - 4.0,
          '民航总医院检验科设备卡片', 11.5, _FONT_BOLD, HexColor("#FFFFFF"))

    body_top = y_top - TITLE_H
    upper_h = ROW_H * TOP_ROWS
    upper_bottom = body_top - upper_h

    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(x0, upper_bottom, CARD_W, upper_h, stroke=0, fill=1)

    # 前 5 行的横线（左 2 列范围）
    c.setStrokeColor(C_LINE)
    c.setLineWidth(0.6)
    for i in range(TOP_ROWS + 1):
        yy = body_top - ROW_H * i
        c.line(x0, yy, x0 + COL_LABEL + COL_VALUE, yy)
    c.line(x0 + COL_LABEL, body_top, x0 + COL_LABEL, upper_bottom)
    c.line(x0 + COL_LABEL + COL_VALUE, body_top, x0 + COL_LABEL + COL_VALUE, upper_bottom)

    upper_rows = [
        ('设备编号', code, _FONT, 9),
        ('设备名称', name, _FONT, 9),
        ('厂家型号', model, _FONT_BOLD, 9),
        ('设备状态', None, _FONT, 7),
        ('设备负责人', owner, _FONT_BOLD, 10),
    ]
    for i, (label, value, vfont, vsize) in enumerate(upper_rows):
        cy = body_top - ROW_H * i - ROW_H / 2 - 3.0
        _text(c, x0 + COL_LABEL / 2, cy, label, 9, _FONT)
        vx = x0 + COL_LABEL + COL_VALUE / 2
        if label == '设备状态':
            _draw_status(c, vx, cy, status, vsize)
        else:
            _text(c, vx, cy, value, vsize, vfont)

    # 「设备负责人」行下方：左 2 列 + 二维码列 各补一段横线（拼成完整一条）
    c.setStrokeColor(C_LINE)
    c.setLineWidth(0.6)
    c.line(x0, upper_bottom, x0 + COL_LABEL + COL_VALUE, upper_bottom)
    c.line(x0 + COL_LABEL + COL_VALUE, upper_bottom, x0 + CARD_W, upper_bottom)

    # ---- 二维码区域 ----
    qx = x0 + COL_LABEL + COL_VALUE
    qw = COL_QR
    qr_size = 1.40 * cm
    qr_top = body_top - 0.14 * cm
    if code:
        full = code if code.startswith('MHZYY-') else 'MHZYY-' + code
        url = f'{host}/repair-fill?code={full}'
        # 文件名带 URL 指纹：协议或主机一变就用新文件，不会命中旧缓存
        import hashlib
        sig = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        png = _make_qr_png(url, os.path.join(qr_dir, f'{full}_{sig}.png'))
        if png:
            try:
                c.drawImage(png, qx + (qw - qr_size) / 2, qr_top - qr_size,
                            width=qr_size, height=qr_size, mask=None)
            except Exception:
                pass
    cap_y = (qr_top - qr_size) - 0.34 * cm
    _text(c, qx + qw / 2, cap_y, '设备故障请扫码', 6.5, _FONT)
    _text(c, qx + qw / 2, cap_y - 0.30 * cm, '填写维修记录', 6.5, _FONT)

    # ---- 下方 4 行（通栏）----
    lower_rows = [
        ('开始使用日期', start),
        ('本次校准时间', cal),
        ('下次校准时间', nextcal),
        ('设备维修联系方式', contact),
    ]
    y = upper_bottom
    for label, value in lower_rows:
        y -= ROW_H
        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.6)
        c.line(x0, y, x0 + CARD_W, y)
        c.line(x0 + COL_LABEL, y, x0 + COL_LABEL, y + ROW_H)
        _text(c, x0 + COL_LABEL / 2, y + ROW_H / 2 - 3.0, label, 9, _FONT)
        _text(c, x0 + COL_LABEL + (CARD_W - COL_LABEL) / 2,
              y + ROW_H / 2 - 3.0, value, 9.5, _FONT_BOLD)

    # ---- 外框 ----
    total_h = TITLE_H + ROW_H * (TOP_ROWS + len(lower_rows))
    c.setStrokeColor(C_LINE)
    c.setLineWidth(1.0)
    c.rect(x0, y_top - total_h, CARD_W, total_h, stroke=1, fill=0)


def build_pdf(items, host: str, qr_dir: str) -> bytes:
    """生成设备卡片 PDF（每页 3 张），返回 bytes"""
    os.makedirs(qr_dir, exist_ok=True)
    _ensure_font()
    if _FONT in ("Helvetica", "Helvetica-Bold"):
        # 没有中文字体 → 会渲染成一堆黑方块，宁可报错也不要出废卡
        raise RuntimeError(
            "容器内缺少中文字体，无法生成设备卡片。"
            "请在 Dockerfile 安装 fonts-wqy-zenhei 后重新部署。"
        )
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    x0 = (page_w - CARD_W) / 2
    card_h = TITLE_H + ROW_H * 9

    y_cur = page_h - 1.2 * cm
    for idx, item in enumerate(items):
        if idx and idx % PER_PAGE == 0:
            c.showPage()
            y_cur = page_h - 1.2 * cm
        _draw_card(c, x0, y_cur, item, qr_dir, host)
        y_cur -= card_h + GAP
    c.save()
    return buf.getvalue()


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name)[:80]
