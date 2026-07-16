"""Convert .doc (Word binary / OLE2) to .docx using Microsoft Word COM.

This module is imported by the backend (running in the backend venv) but the
actual Word automation requires Microsoft Word + pywin32, which live in the
*system* Python on this host. So `convert_doc_bytes_to_docx` shells out to the
system Python interpreter to run this same file as a CLI (the ``__main__`` block
calls `win_convert`, which imports win32com at runtime and is never imported by
the backend).

Usage (CLI):  python doc_convert.py <input.doc> <output.docx>
Exit code 0 = success, non-zero = failure.
"""
import os
import sys
import tempfile
import subprocess

# 系统 Python（含 pywin32 + Microsoft Word），本机路径
SYSTEM_PYTHON = r"C:\Users\81526\AppData\Local\Programs\Python\Python314\python.exe"

# wdFormatXMLDocument
WD_FORMAT_XML = 16


def _script_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc_convert.py")


def win_convert(input_path: str, output_path: str) -> bool:
    """Convert a single .doc file to .docx. Must run under a Python with pywin32."""
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = None
    try:
        doc = word.Documents.Open(os.path.abspath(input_path), ReadOnly=True)
        doc.SaveAs(os.path.abspath(output_path), FileFormat=WD_FORMAT_XML)
        return True
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            word.Quit()
        except Exception:
            pass


def convert_doc_bytes_to_docx(content: bytes, timeout: int = 120) -> bytes | None:
    """Convert .doc bytes to .docx bytes. Returns docx bytes, or None on failure."""
    if not content:
        return None
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "src.doc")
        dst = os.path.join(td, "dst.docx")
        with open(src, "wb") as f:
            f.write(content)
        try:
            proc = subprocess.run(
                [SYSTEM_PYTHON, _script_path(), src, dst],
                timeout=timeout,
                capture_output=True,
            )
        except Exception as e:  # noqa: BLE001
            print("[doc_convert] subprocess error:", e, file=sys.stderr)
            return None
        if proc.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
            with open(dst, "rb") as f:
                return f.read()
        err = proc.stderr.decode("utf-8", errors="ignore")[:400]
        print(f"[doc_convert] failed rc={proc.returncode} {err}", file=sys.stderr)
        return None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python doc_convert.py <input.doc> <output.docx>")
        sys.exit(2)
    try:
        win_convert(sys.argv[1], sys.argv[2])
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
