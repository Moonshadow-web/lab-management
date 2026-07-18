import os, openpyxl
d = r"C:/Users/81526/Desktop/2026年6月室内室间比对结果(2)/2026年6月室内室间比对结果"
path = os.path.join(d, "BG-SM-CZ-025-定量室内比对结果分析表（生化分析仪）.xlsx")
wb = openpyxl.load_workbook(path, data_only=True)
ws = wb["生化分析仪比对"]
print("=== 生化分析仪比对 sheet ===")
print("dims", ws.dimensions, "maxrow", ws.max_row, "maxcol", ws.max_column)
# row3 full (level markers)
print("row3:", [ws.cell(row=3, column=c).value for c in range(1, ws.max_column + 1)])
# row4 full (header)
print("row4:", [ws.cell(row=4, column=c).value for c in range(1, ws.max_column + 1)])
# find max level: scan row3 for 水平N
levels = [ws.cell(row=3, column=c).value for c in range(1, ws.max_column + 1) if str(ws.cell(row=3, column=c).value or "").startswith("水平")]
print("levels found in row3:", levels)
# print last data rows
print("--- last 10 rows (col1-3) ---")
for rr in range(ws.max_row - 9, ws.max_row + 1):
    print(f"  row{rr}:", [ws.cell(row=rr, column=c).value for c in range(1, 4)])
print()
# explore other sheets
for sn in ["竖版", "横版"]:
    ws2 = wb[sn]
    print(f"=== sheet {sn} dims {ws2.dimensions} maxrow {ws2.max_row} maxcol {ws2.max_column} ===")
    for rr in range(1, min(ws2.max_row, 6) + 1):
        print(f"  row{rr}:", [ws2.cell(row=rr, column=c).value for c in range(1, min(ws2.max_column, 10) + 1)])
