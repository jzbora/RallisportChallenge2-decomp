"""Check the fork's added files before pushing source changes."""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parent.parent
paths=subprocess.check_output(['git','diff','--name-only','--diff-filter=A','upstream/main','dev'],cwd=root).decode().splitlines()
forbidden={'.xbe','.iso','.xiso','.fa','.str','.bik','.profile','.exe','.dll','.zip','.ttf','.otf','.ttc'}
secret=re.compile(rb'(?:ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
errors=[]
for name in paths:
    p=Path(name)
    if p.suffix.lower() in forbidden or any(part.lower() in {'udata','tdata','portable-data','rallisport2','logs'} for part in p.parts):errors.append(name+': generated/private file')
    data=subprocess.check_output(['git','show','dev:'+name],cwd=root)
    if len(data)>2_000_000:errors.append(name+': unexpectedly large')
    if secret.search(data):errors.append(name+': possible credential')
if errors: raise SystemExit('\n'.join(errors))
print(f'PASS: {len(paths)} added source/documentation files; no game assets, saves, font binaries or credential patterns')
