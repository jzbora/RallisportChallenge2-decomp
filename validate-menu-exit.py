import runpy,struct,json
from pathlib import Path
m=runpy.run_path('menu-exit-assets.py')
stock=Path('RalliSport2/Layer0/MenuHDD.fa').read_bytes()
patched=Path('menu-exit-output/MenuHDD.fa').read_bytes()
old,files,table,n,blocks=m['archive_read'](stock)
new,nfiles,ntable,nn,nblocks=m['archive_read'](patched)
assert n==nn and files==nfiles
changes=[];unchanged=0
for i in range(n):
    p=files+i*64
    a=m['unpack_entry'](stock,old,p,table)
    b=m['unpack_entry'](patched,new,p,ntable)
    if a==b:unchanged+=1;continue
    _,count,_,entries,_,base=struct.unpack_from('<6I',a)
    for j in range(count):
        q=entries+j*136
        name=a[q:q+128].split(b'\0')[0].decode('ascii')
        ao,an=struct.unpack_from('<II',a,q+128)
        bo,bn=struct.unpack_from('<II',b,q+128)
        before=a[base+ao:base+ao+an];after=b[base+bo:base+bo+bn]
        if before==after:unchanged+=1;continue
        assert name.endswith(('/pause/pausescreen','/mainmenu/mainmenuscreen')),name
        # Verify exactly the independently regenerated appended choice.
        target=('Pause/PauseChoices',13) if '/pause/' in name else ('MainMenu/Choices',7)
        expected,choices=m['add_choice'](before,*target)
        assert after==expected
        assert len({key for text,key in choices})==len(choices)
        assert target[1] not in {key for text,key in choices}
        changes.append({'screen':name,'original_choices':len(choices),'new_choices':len(choices)+1})
assert len(changes)==2
zh=runpy.run_path('chinese-pilot.py')
for label,path in [('english','RalliSport2'),('chinese','menu-exit-backup-2026-10-20')]:
    original=Path(path)/('Locale/English/localestrings.str' if label=='english' else 'localestrings.str')
    a=zh['parse_locale'](original.read_bytes())[1]
    b=zh['parse_locale'](Path('menu-exit-output',label+'-localestrings.str').read_bytes())[1]
    assert all(b[k]==v for k,v in a.items())
    assert b.keys()-a.keys()=={0xF000,0xF001}
    if label=='chinese':assert not (set(b[0xF000]+b[0xF001])-set(zh['CHARS'])-set('\r\n'))
report={'screens':changes,'other_resources_preserved':unchanged,'existing_locale_strings_preserved':True}
Path('logs/menu-exit-assets-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
