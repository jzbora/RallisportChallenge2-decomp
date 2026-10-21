"""Fetch an OFL font from a pinned official Noto CJK revision (not committed)."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json
root=Path(__file__).resolve().parent.parent
revision='f8d157532fbfaeda587e826d4cd5b21a49186f7c'
base=f'https://raw.githubusercontent.com/notofonts/noto-cjk/{revision}/'
font=root/'third_party/fonts/NotoSansCJKsc-Bold.otf'
license_file=root/'licenses/NotoCJK-OFL.txt'
for source,target in [('Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf',font),('Sans/LICENSE',license_file)]:
    target.parent.mkdir(parents=True,exist_ok=True)
    with urlopen(base+source,timeout=60) as response: data=response.read()
    if target==font and data[:4]!=b'OTTO': raise ValueError('Expected an OpenType font')
    target.write_bytes(data)
print(json.dumps({'revision':revision,'font':str(font),'sha256':hashlib.sha256(font.read_bytes()).hexdigest()},indent=2))
