import os, sys
import fitz  # pymupdf

PDF = r"C:/Users/81526/Desktop/2026年室间质量评价计划活动安排(单月终版).pdf"
OUTDIR = r"D:/workbuddyprojects/网页版-生免速查工具/outputs/nhc_pages"
os.makedirs(OUTDIR, exist_ok=True)

doc = fitz.open(PDF)
print("PAGES", len(doc), file=sys.stderr)
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))  # ~100-130 dpi
    p = os.path.join(OUTDIR, f"page_{i+1:02d}.png")
    pix.save(p)
print("RENDERED", len(doc), file=sys.stderr)
