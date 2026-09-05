"""HTTP 响应头相关的公共工具。"""

from urllib.parse import quote


def content_disposition(disposition: str, filename: str) -> str:
    """生成带 RFC 5987 UTF-8 文件名的内容处置头（中文名安全）。

    背景：HTTP 响应头只能按 latin-1 编码，若把中文文件名直接写进
    ``filename="..."``，Starlette 编码响应头时会抛
    ``UnicodeEncodeError: 'latin-1' codec can't encode characters``，
    表现为接口 **500 Internal Server Error**（而不是下载失败提示）。

    正确做法：``filename=`` 只放 ASCII 回退名，真实文件名用
    ``filename*=UTF-8''<urlencoded>`` 传递（RFC 5987）。

    用法::

        headers={"Content-Disposition": content_disposition("attachment", fname)}
    """
    ascii_name = (filename or "").encode("ascii", "ignore").decode("ascii") or "download"
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename or "")}'
