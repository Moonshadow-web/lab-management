import os, openpyxl
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
files = {
    "生化": "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx",
    "DXI800": "BG-SM-CZ-024-定量室内比对结果记录分析表（DXI800分析仪）.xlsx",
    "早孕": "BG-SM-CZ-027-定量室内比对结果记录分析表（早孕系列）.xlsx",
}
import datetime
for name, fn in files.items():
    path = os.path.join(d, fn)
    wb = openpyxl.load_workbook(path, data_only=True)
    print("=" * 60, name, "sheets:", wb.sheetnames)
    for ws in wb.worksheets:
        print(f"  -- sheet '{ws.title}' dims {ws.dimensions}")
        for rr in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                v = ws.cell(row=rr, column=c).value
                if v is None:
                    continue
                s = str(v)
                hit = False
                # datetime values
                if isinstance(v, (datetime.datetime, datetime.date)):
                    hit = True
                # text with 日期 / 年 / 月 / 日 / 比
                if any(k in s for k in ("日期", "年", "月", "日", "比", "2026", "2025")) and len(s) < 40:
                    hit = True
                # number like 20260615 or 6/15
                if isinstance(v, (int, float)) and ("2026" in s or "2025" in s):
                    hit = True
                if hit:
                    print(f"    ({rr},{c}) {v!r}")
