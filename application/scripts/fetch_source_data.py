"""Fetch or verify the exact open official LSMS-ISA v2.0 source files.

Uses the fixed URLs, official MD5 checksums and independently recorded SHA256
in data/raw/source_data_manifest.json. The offline workflow does not call this.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digests(path):
 md5=hashlib.md5();sha=hashlib.sha256();size=0
 with path.open('rb')as f:
  while block:=f.read(1024*1024):md5.update(block);sha.update(block);size+=len(block)
 return size,md5.hexdigest(),sha.hexdigest()
def verify(path,row):
 size,md5,sha=digests(path)
 if size!=row['size_bytes']or'md5:'+md5!=row['checksum']or sha!=row['sha256']:raise ValueError('Source checksum/size mismatch: '+row['file'])
 print('Verified '+row['file']+' (MD5 and SHA256)',flush=True)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output-dir',type=Path,default=ROOT/'data/raw/lsms_isa');ap.add_argument('--files',nargs='+',help='Selected source filenames; default is all four files.');ap.add_argument('--list',action='store_true',help='List fixed sources without downloading.');ap.add_argument('--verify-only',action='store_true',help='Only verify existing files, without making network requests.');a=ap.parse_args()
 meta=json.loads((ROOT/'data/raw/source_data_manifest.json').read_text());rows=meta['files']
 if a.files:
  unknown=set(a.files)-{r['file']for r in rows}
  if unknown:ap.error('Unknown source filenames: '+', '.join(sorted(unknown)))
  rows=[r for r in rows if r['file']in a.files]
 if a.list:
  print(json.dumps({'doi':meta['doi'],'version':meta['version'],'license':meta['license'],'selected_bytes':sum(r['size_bytes']for r in rows),'files':rows},indent=2));return
 out=a.output_dir.expanduser().resolve()
 for row in rows:
  dest=out/row['file']
  if dest.exists():verify(dest,row);continue
  if a.verify_only:raise FileNotFoundError('Missing selected source: '+row['file'])
  out.mkdir(parents=True,exist_ok=True);temp=dest.with_suffix(dest.suffix+'.download')
  print('Downloading '+row['file']+' ('+str(row['size_bytes'])+' bytes) from '+row['url'],flush=True)
  try:
   with urllib.request.urlopen(row['url'],timeout=120)as response,temp.open('wb')as f:
    while block:=response.read(1024*1024):f.write(block)
   verify(temp,row);temp.replace(dest)
  except Exception:
   if temp.exists():temp.unlink()
   raise
 print('Selected official source files are ready.')
if __name__=='__main__':main()
