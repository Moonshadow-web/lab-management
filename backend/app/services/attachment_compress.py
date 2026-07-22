"""附件图片压缩：在存入 MySQL BLOB 前把大图压到合理体积。

背景：附件字节直接存 MySQL LONGBLOB，但单条 INSERT 仍受服务端
``max_allowed_packet`` 限制（CloudBase TDSQL-C 默认约 4MB）。手机拍的纸质
原始结果常为 3~8MB，超阈值会 INSERT 失败 → 上传 500。

策略：上传时对图片字节做「缩放 + JPEG 重编码」，把长边限制在 2400px、
质量 85，通常从几 MB 降到几百 KB，稳稳低于阈值；非图片或压缩后反而更大
则原样返回（不破坏小图/透明 PNG）。Pillow 不可用时安全降级为原字节。
"""
from __future__ import annotations

import io

try:
    from PIL import Image

    _HAS_PIL = True
except Exception:  # noqa: BLE001  Pillow 缺失时降级
    _HAS_PIL = False

MAX_SIDE = 2400  # 长边上限（px）
JPEG_QUALITY = 85


def optimize_image_bytes(raw: bytes, ext: str) -> bytes:
    """对图片字节做有损压缩/缩放；非图片或压缩后反而更大则原样返回。"""
    if not _HAS_PIL or not raw:
        return raw
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()  # 触发真实解码，坏图在此抛异常 → 降级
    except Exception:  # noqa: BLE001
        return raw

    try:
        w, h = img.size
        scale = min(1.0, MAX_SIDE / max(w, h))
        if scale < 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

        # 透明通道：贴白底后转 RGB（JPEG 不支持透明）
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            try:
                bg.paste(img, mask=img.split()[-1])
            except Exception:  # noqa: BLE001
                bg = img.convert("RGB")
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        compressed = out.getvalue()
        # 仅当压缩后更小才采用，避免小 PNG 转 JPEG 反而变大
        return compressed if len(compressed) < len(raw) else raw
    except Exception:  # noqa: BLE001
        return raw
