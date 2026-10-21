"""Add a native controller-selectable Quit choice to the two menu screens.

Always reads original archives; writes separate output files, never game saves.
"""
from pathlib import Path
import importlib.util, struct, zlib

def u32(b,p): return struct.unpack_from('<I',b,p)[0]
def put(b,p,v): struct.pack_into('<I',b,p,v)
def align(b,n): b.extend(bytes(-len(b)%n))

def archive_read(b):
    index=bytearray(zlib.decompress(b[8:]))
    # v1 header: byte version, uint24 file count, uint16 dirs, uint16 blocks.
    files=int.from_bytes(index[1:4],'little')
    dirs,blocks=struct.unpack_from('<HH',index,4)
    return index,8+dirs*32,8+dirs*32+files*64,files,blocks

def unpack_entry(b,index,p,table):
    off,size,first,count=struct.unpack_from('<IIHH',index,p+8)
    out=bytearray(size)
    for i in range(first,first+count):
        comp,ln,co,ro=struct.unpack_from('<4I',index,table+i*16)
        base=u32(b,4)
        packed=b[base+off+co:base+off+co+comp]
        chunk=packed if comp==ln else zlib.decompress(packed)
        assert len(chunk)==ln
        out[ro:ro+ln]=chunk
    return out

def meme_strings(b):
    strings=[];pos=0
    while b[pos]:
        n=b[pos]; strings.append(b[pos+1:pos+1+n].decode('ascii'));pos+=n+1
    return strings,pos+1

def add_choice(b,list_name,choice_id):
    strings,start=meme_strings(b)
    name=strings.index(list_name); typ=strings.index('dice::meme::RscChoiceBarChoiceListData')
    choice_type=strings.index('dice::meme::RscChoiceBarChoiceData')
    string_type=strings.index('dice::meme::RscStringData')
    marker=struct.pack('<HHI',name,typ,1)
    pos=b.find(marker,start)-4
    assert pos>=start and b.find(marker,pos+5)==-1
    end=pos+u32(b,pos)
    # Each choice is a 38-byte object: StringData(locale id), target, action id.
    records=[];p=pos+12
    while u32(b,p)==38:
        assert struct.unpack_from('<HHI',b,p+4)==(0,choice_type,2)
        assert struct.unpack_from('<HH',b,p+16)==(0,string_type)
        records.append(p);p+=38
    assert p+12==end, (hex(p),hex(end))
    record=bytearray(b[records[-1]:records[-1]+38])
    put(record,20,0xF000)  # QUIT GAME, shared by both editions.
    put(record,28,0)      # no screen target
    put(record,32,choice_id)
    result=bytearray(b[:p]+record+b[p:])
    put(result,pos,u32(b,pos)+38)
    # The list is top-level in these MemeFiles: no enclosing object lengths.
    assert sum(1 for j in range(start,pos) if j+u32(b,j)==end)==0
    return result,[(u32(b,r+20),u32(b,r+32)) for r in records]

def patch_resource(b):
    version,nt,nf,table,ft,data=struct.unpack_from('<6I',b)
    result=bytearray(b);changes=[]
    for i in range(nt):
        p=table+i*136
        name=b[p:p+128].split(b'\0')[0].decode('ascii')
        target=None
        if name.endswith('/pause/pausescreen'): target=('Pause/PauseChoices',13)
        elif name.endswith('/mainmenu/mainmenuscreen'): target=('MainMenu/Choices',7)
        if target:
            off,size=struct.unpack_from('<II',b,p+128)
            raw=b[data+off:data+off+size]
            # The front end names its list differently on some retail builds.
            if target[0] not in meme_strings(raw)[0]:
                print('LIST CANDIDATES',name,meme_strings(raw)[0]);raise ValueError(target)
            patched,original=add_choice(raw,*target)
            align(result,128)
            struct.pack_into('<II',result,p+128,len(result)-data,len(patched))
            result+=patched
            changes.append((name,original))
    return result,changes

def patch_archive(b):
    index,files,table,nf,blocks=archive_read(b)
    output=bytearray(b[u32(b,4):]);changes=[]
    for i in range(nf):
        p=files+i*64
        if index[p+20:p+64].split(b'\0')[0]!=b'menu.res':continue
        raw=unpack_entry(b,index,p,table)
        patched,found=patch_resource(raw)
        if not found:continue
        off,size,first,count=struct.unpack_from('<IIHH',index,p+8)
        align(output,2048);new_off=len(output);rel=0
        count=(len(patched)+131071)//131072
        first=blocks
        for j in range(count):
            chunk=patched[j*131072:(j+1)*131072];compressed=zlib.compress(chunk,9)
            align(output,2048);rel=len(output)-new_off
            index+=struct.pack('<4I',len(compressed),len(chunk),rel,j*131072)
            output+=compressed
        struct.pack_into('<IIHH',index,p+8,new_off,len(patched),first,count)
        blocks+=count
        changes+=found
    struct.pack_into('<H',index,6,blocks)
    packed=zlib.compress(index,9)
    # Header carries compressed index length and payload base.
    print('archive header',struct.unpack('<II',b[:8]),'new compressed',len(packed))
    base=(8+len(packed)+2047)//2048*2048
    return struct.pack('<II',len(packed),base)+packed+bytes(base-8-len(packed))+output,changes

def locale(b,chinese,parser=None):
    if parser is None:
        spec=importlib.util.spec_from_file_location('zh',Path(__file__).with_name('chinese-pilot.py'))
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        parser=mod.parse_locale
    pairs,values,names,oldend=parser(b)
    extra={0xF000:'退出游戏' if chinese else 'QUIT GAME',
           0xF001:'确定退出游戏吗？\r\n尚未保存的比赛进度将丢失。' if chinese else 'Quit the game?\r\nUnsaved race progress will be lost.'}
    assert all(values[k]==extra[k] for k in values.keys()&extra.keys())
    values.update(extra);table=bytearray();text=bytearray()
    for key in sorted(values):
        table+=struct.pack('<HI',key,len(text)//2)
        text+=values[key].encode('utf-16le')+b'\0\0'
    table+=struct.pack('<HI',0xffff,len(text)//2)
    block=struct.pack('<II',8+len(table)+len(text),len(values))+table+text
    head=bytearray(b[:28]);delta=len(block)-(oldend-28)
    for off in (16,20,24):put(head,off,u32(head,off)+delta)
    result=head+block+b[oldend:]
    assert parser(result)[1]==values
    return result

if __name__=='__main__':
    out=Path('menu-exit-output');out.mkdir(exist_ok=True)
    result,changes=patch_archive(Path('RalliSport2/Layer0/MenuHDD.fa').read_bytes())
    print(changes)
    assert len(changes)==2,changes
    (out/'MenuHDD.fa').write_bytes(result)
    for label,source in [('english','RalliSport2'),('chinese','rsc2-zh-pilot/game')]:
        (out/(label+'-localestrings.str')).write_bytes(locale((Path(source)/'Locale/English/localestrings.str').read_bytes(),label=='chinese'))
