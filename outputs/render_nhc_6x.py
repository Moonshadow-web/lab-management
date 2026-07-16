import os, sys
import fitz

PDF = r"C:/Users/81526/Desktop/2026年室间质量评价计划活动安排(单月终版).pdf"
OUTDIR = r"D:/workbuddyprojects/网页版-生免速查工具/outputs/nhc_pages_6x"
os.makedirs(OUTDIR, exist_ok=True)

doc = fitz.open(PDF)
for i in [2, 3]:  # March and April (0-indexed)
    page = doc.load_page(i)
    pix = page.get_pixmap(matrix=fitz.Matrix(6.0, 6.0))
    p = os.path.join(OUTDIR, f"page_{i+1:02d}_6x.png")
    pix.save(p)
print("RENDERED 6x pages 3,4", file=sys.stderr)
