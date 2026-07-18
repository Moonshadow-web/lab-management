import os, glob, openpyxl
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
files = {
    "生化": "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx",
    "DXI800": "BG-SM-CZ-024-定量室内比对结果记录分析表（DXI800分析仪）.xlsx",
    "早孕": "BG-SM-CZ-027-定量室内比对结果记录分析表（早孕系列）.xlsx",
}
for name, fn in files.items():
    path = os.path.join(d, fn)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    print("=" * 70)
    print(name, fn, "dims", ws.dimensions, "maxrow", ws.max_row, "maxcol", ws.max_column)
    # print first 4 rows fully
    for rr in range(1, 5):
        vals = [ws.cell(row=rr, column=c).value for c in range(1, ws.max_column + 1)]
        print(f"  row{rr}:", vals)
    # find any cell containing 日期/date/年/月
    print("  -- scan for date-like cells --")
    for rr in range(1, min(ws.max_row, 12) + 1):
        for c in range(1, min(ws.max_column, 6) + 1):
            v = ws.cell(row=rr, column=c).value
            if v is not None and (("日期" in str(v)) or ("年" in str(v)) or ("月" in str(v)) or ("比" in str(v))):
                print(f"    ({rr},{c})={v!r}")
