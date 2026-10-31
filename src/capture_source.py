"""Capture the indexed official fixed BTS archive; native records remain private."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,zipfile
import requests
ROOT=Path(__file__).resolve().parents[1]
def run(out):
    source=json.loads((ROOT/'data/source_contract.json').read_bytes())
    out=out.resolve();out.mkdir(exist_ok=False)
    url=source['direct_archive_url']
    assert url=='https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_1.zip'
    started=datetime.now(timezone.utc).isoformat()
    with requests.get(url,timeout=45,stream=True) as response:
        receipt=dict(url=url,status=response.status_code,started_utc=started,content_type=response.headers.get('Content-Type'),advertised_bytes=response.headers.get('Content-Length'),last_modified=response.headers.get('Last-Modified'))
        (out/'request.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
        response.raise_for_status()
        target=out/'native.zip';size=0;digest=hashlib.sha256()
        with target.open('wb') as stream:
            for chunk in response.iter_content(1024*1024):
                if chunk:
                    size+=len(chunk);assert size<=300_000_000,'bounded archive size'
                    digest.update(chunk);stream.write(chunk)
    assert size==source['indexed_archive_bytes'],'same published archive size'
    if receipt['advertised_bytes'] is not None:assert size==int(receipt['advertised_bytes'])
    members=[]
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None,'ZIP CRC controls'
        for item in archive.infolist():
            if item.is_dir():continue
            raw=archive.read(item.filename)
            members.append(dict(name=item.filename,bytes=len(raw),compressed_bytes=item.compress_size,crc32=item.CRC,sha256=hashlib.sha256(raw).hexdigest()))
    receipt.update(status='PASS_NATIVE_CAPTURE',http_status=200,bytes=size,sha256=digest.hexdigest(),completed_utc=datetime.now(timezone.utc).isoformat(),members=members,
                   scope='Exact indexed January2024 reporting-carrier archive;not original publication,unchanging historical truth or Europe-matched data.')
    (out/'capture_receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    (ROOT/'data/capture_receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps(receipt))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
