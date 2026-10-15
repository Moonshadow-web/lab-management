# -*- coding: utf-8 -*-
"""上传单个性能验证报告 → verification_reports + report_archives。

用法：
  python scripts/upload_vrf.py <xlsx路径> [qualitative|quantitative]

不传类型时默认 quantitative（定量）。定性项目（乙肝/HIV/梅毒等）传 qualitative。
"""
import json, sys, urllib.request, urllib.parse, urllib.error
from pathlib import Path

BASE = 'https://lab-management-282724-9-1408547492.sh.run.tcloudbase.com'


def login():
    p = urllib.parse.urlencode({'username': 'jinzizheng', 'password': 'Jzz6827556'}).encode()
    d = json.loads(urllib.request.urlopen(urllib.request.Request(
        BASE + '/api/v1/auth/login', data=p,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}), timeout=20).read().decode())
    return d['access_token']


def upload(token, fp: Path, report_type: str):
    boundary = '----wb_vrf_upload'
    content = fp.read_bytes()
    body = f'--{boundary}\r\nContent-Disposition: form-data; name="report_type"\r\n\r\n{report_type}\r\n'.encode('utf-8')
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{fp.name}"\r\n'
        'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
    ).encode('utf-8')
    body += content + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    req = urllib.request.Request(BASE + '/api/v1/report-archives/upload', method='POST', data=body,
                                headers={'Authorization': 'Bearer ' + token,
                                         'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    fp = Path(sys.argv[1])
    report_type = sys.argv[2] if len(sys.argv) > 2 else 'quantitative'
    if not fp.exists():
        print(f'文件不存在: {fp}')
        sys.exit(1)
    if report_type not in ('quantitative', 'qualitative'):
        print(f'report_type 只能是 quantitative/qualitative，收到: {report_type}')
        sys.exit(1)

    token = login()
    print(f'上传: {fp.name}（{report_type}）')
    try:
        r = upload(token, fp, report_type)
        print(f"OK  vid={r.get('verification_id')} project={r.get('project_name')} "
              f"type={r.get('report_type')} archive={r.get('archive_id') or r.get('id')}")
    except urllib.error.HTTPError as e:
        print(f'FAIL HTTP {e.code}: {e.read().decode()[:300]}')
        sys.exit(2)
    except Exception as e:
        print(f'FAIL {e}')
        sys.exit(2)


if __name__ == '__main__':
    main()
