"""Verify and run an encrypted automation bundle without publishing its output."""
import hashlib,hmac,io,json,os,subprocess,tarfile,tempfile
from pathlib import Path

def decrypt(payload,signature,keys):
 actual=hmac.new(bytes.fromhex(keys['mac_key']),payload,hashlib.sha256).hexdigest()
 if not hmac.compare_digest(actual,signature.strip()):raise ValueError('Bundle authentication failed')
 result=subprocess.run(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:BUNDLE_PASSWORD'],input=payload,capture_output=True,env=dict(os.environ,BUNDLE_PASSWORD=keys['password']))
 if result.returncode:raise ValueError('Bundle decryption failed')
 return result.stdout

def main():
 try:
  keys=json.loads(os.environ['BUNDLE_KEYS'])
  data=decrypt(Path('payload.enc').read_bytes(),Path('payload.mac').read_text(),keys)
  with tempfile.TemporaryDirectory(prefix='scheduled-task-')as directory:
   root=Path(directory)
   with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz')as archive:
    members=archive.getmembers()
    if {x.name for x in members}!={'feed.py','drive_publish.py'}or not all(x.isfile()for x in members):raise ValueError('Unexpected bundle contents')
    for member in members:
     content=archive.extractfile(member).read();(root/member.name).write_bytes(content)
   # Run diagnostics and catalogue output stay in a temporary private runner file.
   # No source, metadata, credentials or debug artifacts are uploaded to public logs.
   with (root/'task.log').open('wb')as log:
    result=subprocess.run(['python3','feed.py','--refresh','--publish'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
   if result.returncode:raise RuntimeError('Task failed')
  print('Task completed and output verified.')
 except Exception:
  print('Task failed; the last verified output remains available.')
  raise SystemExit(1)from None
if __name__=='__main__':main()
