# -*- coding: utf-8 -*-
"""
批量把目录下的旧版 .doc (Word 97-2003) 转换为 .docx。
使用本机已安装的 Microsoft Word 的 COM 引擎做"另存为"，无损保留排版。
原 .doc 文件保留不动；输出同名 .docx 到同一目录。
"""
import os
import sys
import time
import traceback

# Word 常量
WD_FORMAT_XML_DOCUMENT = 12        # wdFormatXMLDocument (.docx)
WD_ALERTS_NONE = 0                 # wdAlertsNone
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 1  # 禁用宏，避免安全风险/弹窗

# 要转换的根目录
DIRS = [
    r"C:\Users\81526\Desktop\待办\DXI",
    r"C:\Users\81526\Desktop\待办\生免组项目作业指导书260723",
]


def collect_doc_files(dirs):
    files = []
    for d in dirs:
        if not os.path.isdir(d):
            print(f"[WARN] 目录不存在，跳过: {d}")
            continue
        for name in os.listdir(d):
            low = name.lower()
            if low.endswith(".doc") and not low.endswith(".docx"):
                files.append(os.path.join(d, name))
    return files


def target_path(doc_path):
    """同名 .docx，去掉文件名末尾的空格，避免 'xxx .docx' 这种怪名。"""
    base = os.path.basename(doc_path)
    stem = base[:-4].rstrip()  # 去掉 .doc 与末尾空白
    return os.path.join(os.path.dirname(doc_path), stem + ".docx")


def main():
    from win32com.client import Dispatch

    doc_files = collect_doc_files(DIRS)
    print(f"找到 {len(doc_files)} 个 .doc 文件")

    word = Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = WD_ALERTS_NONE
    word.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE

    ok, skip, fail = [], [], []
    try:
        for i, f in enumerate(doc_files, 1):
            tgt = target_path(f)
            if os.path.exists(tgt):
                print(f"[{i}/{len(doc_files)}] 跳过(已存在): {os.path.basename(tgt)}")
                skip.append(f)
                continue
            try:
                doc = word.Documents.Open(
                    os.path.abspath(f),
                    ConfirmConversions=False,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                )
                doc.SaveAs2(os.path.abspath(tgt), FileFormat=WD_FORMAT_XML_DOCUMENT)
                doc.Close(False)
                size = os.path.getsize(tgt)
                print(f"[{i}/{len(doc_files)}] OK  -> {os.path.basename(tgt)} ({size} B)")
                ok.append(f)
            except Exception as e:
                print(f"[{i}/{len(doc_files)}] FAIL -> {os.path.basename(f)}: {e}")
                fail.append((f, str(e)))
                # 尝试关闭可能已经打开的文档，避免卡住
                try:
                    word.Documents.Close(False)
                except Exception:
                    pass
    finally:
        try:
            word.Quit()
        except Exception:
            pass

    print("\n===== 汇总 =====")
    print(f"成功: {len(ok)}")
    print(f"跳过(已存在): {len(skip)}")
    print(f"失败: {len(fail)}")
    if fail:
        print("失败清单:")
        for f, msg in fail:
            print(f"  - {f}: {msg}")
    return len(fail)


if __name__ == "__main__":
    sys.exit(main())
