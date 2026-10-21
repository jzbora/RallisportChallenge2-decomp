import os,subprocess,sys,time,json
from pathlib import Path
root=Path(__file__).resolve().parent
import argparse
parser=argparse.ArgumentParser(description='Headless controller test in an isolated local installation')
parser.add_argument('tag')
parser.add_argument('--install',type=Path,required=True)
parser.add_argument('--script',required=True,help='Timed controller input, in milliseconds')
parser.add_argument('--timeout',type=int,default=120)
args=parser.parse_args()
pilot=args.install.resolve()
frames=root/'logs'/args.tag;frames.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(RSC2_LAUNCHER='0',RECOMP_FB_WINDOW='0',RECOMP_VK_SCALE='1',
           RECOMP_VK_MSAA='0',RECOMP_VK_AO='0',RECOMP_VK_ANISO='1',RECOMP_HDR='0',
           RECOMP_FLIP_HZ='60',RECOMP_FPS_OVERLAY='0',RECOMP_VK_STATS='0',
           RECOMP_FB_DUMP_AT=str(frames)+':'+','.join(map(str,range(150,36001,150))),
           RECOMP_PAD_LIVE=str(pilot/'reload-input.txt'))
env['RECOMP_PAD_SCRIPT']=args.script
(pilot/'reload-input.txt').write_text('')
with (frames/'stdout.log').open('wb') as out,(frames/'stderr.log').open('wb') as err:
    p=subprocess.Popen([str(pilot/'rsc2.exe')],cwd=pilot,env=env,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (frames/'pid.txt').write_text(str(p.pid))
    try: code=p.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        p.terminate();p.wait(timeout=10)
        raise SystemExit('Timed out; check the captured frames and adjust the input timeline')
log=(frames/'stderr.log').read_text(errors='replace')
if code!=0 or '[MENU EXIT] response 0' not in log: raise SystemExit('Native menu exit was not confirmed')
print(json.dumps({'exit_code':code,'native_exit':True,'cancel_observed':'[MENU EXIT] response 1' in log}))
