import os,subprocess,sys,time,json
from pathlib import Path
root=Path(__file__).resolve().parent
pilot=root/'rsc2-zh-pilot'
tag=sys.argv[1]
frames=root/'logs'/tag;frames.mkdir(exist_ok=True)
env=os.environ.copy()
env.update(RSC2_LAUNCHER='0',RECOMP_FB_WINDOW='0',RECOMP_VK_SCALE='1',
           RECOMP_VK_MSAA='0',RECOMP_VK_AO='0',RECOMP_VK_ANISO='1',RECOMP_HDR='0',
           RECOMP_FLIP_HZ='60',RECOMP_FPS_OVERLAY='0',RECOMP_VK_STATS='0',
           RECOMP_FB_DUMP_AT=str(frames)+':'+','.join(map(str,range(150,36001,150))),
           RECOMP_PAD_LIVE=str(pilot/'reload-input.txt'))
env['RECOMP_PAD_SCRIPT']=sys.argv[2] if len(sys.argv)>2 else '5000:start,8000:start,11000:a,45000:a,50000:up,52000:a,57000:b,61000:a,65000:left,67000:a'
(pilot/'reload-input.txt').write_text('')
with (frames/'stdout.log').open('wb') as out,(frames/'stderr.log').open('wb') as err:
    p=subprocess.Popen([str(pilot/'rsc2.exe')],cwd=pilot,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
(frames/'pid.txt').write_text(str(p.pid))
print(p.pid)
