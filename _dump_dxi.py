import os, openpyxl
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
for name, fn in {
    "DXI800": "BG-SM-CZ-024-定量室内比对结果记录分析表（DXI800分析仪）.xlsx",
    "早孕": "BG-SM-CZ-027-定量室内比对结果记录分析表（早孕系列）.xlsx",
}.items():
    wb = openpyxl.load_workbook(os.path.join(d, fn), data_only=True)
    ws = wb.active
    print("=" * 70, name, "dims", ws.dimensions, "maxrow", ws.max_row)
    for rr in range(1, ws.max_row + 1):
        vals = [ws.cell(row=rr, column=c).value for c in range(1, ws.max_column + 1)]
        if any(v is not None for v in vals):
            print(f"  r{rr}:", vals)
