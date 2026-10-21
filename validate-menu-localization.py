"""Validate localized assets against the unmodified disc resources."""
from pathlib import Path
import json, re, runpy, struct
from PIL import Image

root = Path(__file__).resolve().parent
mod = runpy.run_path(str(root/'chinese-pilot.py'))
source, output = root/'RalliSport2', root/'rsc2-zh-pilot/game'
translations = mod['TRANSLATIONS']
_, original_text, names, _ = mod['parse_locale']((source/'Locale/English/localestrings.str').read_bytes())
_, translated_text, new_names, _ = mod['parse_locale']((output/'Locale/English/localestrings.str').read_bytes())
assert names == new_names
formats = re.compile(r'%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hlLjzt])?[diuoxXfFeEgGaAcCsSpn%]')
changed = {names[key]: text for key, text in translations.items()}
for key, text in original_text.items():
    assert translated_text[key] == changed.get(key, text), key
    assert formats.findall(text) == formats.findall(translated_text[key]), key
for key, idx in names.items():
    if original_text[idx] and key.startswith(('LID_HEAD_', 'LID_CHOICE_', 'LID_HELP_', 'LID_A_', 'LID_B_', 'LID_X_', 'LID_Y_')):
        assert key in translations, key
    if original_text[idx] and key.startswith(('LID_INGAME_RESULT_', 'LID_INGAME_LINEUP_', 'LID_VOICEMASK_')):
        assert key in translations, key

def fonts(path):
    return mod['unpack_fonts'](path.read_bytes())[1]

font_checks = []
for (_, name, old), (_, new_name, new) in zip(fonts(source/'Layer0/FontsEnglish.fa'), fonts(output/'Layer0/FontsEnglish.fa')):
    assert name == new_name
    oh, nh = struct.unpack_from('<6I', old), struct.unpack_from('<6I', new)
    assert oh[:5] == nh[:5]
    for i in range(oh[1]):
        def extract(res, h):
            o, n = struct.unpack_from('<II', res, h[3]+i*136+128)
            m = res[h[5]+o:h[5]+o+n]
            version, w, height, size, count = struct.unpack_from('<5I', m)
            records = [m[20+j*36:20+(j+1)*36] for j in range(count)]
            codes = [struct.unpack_from('<I', rec, 32)[0] for rec in records]
            assert codes == sorted(set(codes))
            tex = struct.unpack_from('<I', res, h[4]+i*188+128)[0]+h[5]
            packed = struct.unpack_from('<I',res,h[4]+i*188+148)[0]
            pitch = ((packed >> 24)+1)*64
            pixels = res[tex:tex+pitch*height]
            assert len(pixels) == pitch*height
            return m, w, height, records, codes, Image.frombytes('L', (w,height),pixels,'raw','L',pitch,1), pixels
        om, ow, height, orec, ocodes, oa, opixels = extract(old, oh)
        nm, nw, nheight, nrec, ncodes, na, npixels = extract(new, nh)
        assert na.crop((0,0,ow,height)).tobytes() == oa.tobytes(), (name,i,'original pixels')
        by_code = dict(zip(ncodes,nrec))
        font_name = old[oh[4]+i*188:oh[4]+i*188+128].split(b'\0')[0].decode('ascii')
        hud_numeric = font_name.endswith(('/rpmfont_12', '/rpmfont_24'))
        if hud_numeric:
            assert nm == om, (font_name,'HUD metrics changed')
            assert (nw,nheight) == (ow,height), (font_name,'HUD atlas resized')
            assert na.tobytes() == oa.tobytes(), (font_name,'HUD pixels changed')
            assert npixels == opixels, (font_name,'HUD padded texture changed')
            ofe, nfe = oh[4]+i*188, nh[4]+i*188
            assert old[ofe+132:ofe+188] == new[nfe+132:nfe+188], (font_name,'HUD texture descriptor changed')
        else:
            assert set(ocodes) | set(map(ord,mod['CHARS'])) <= by_code.keys()
        for code, rec in zip(ocodes,orec):
            assert by_code[code][8:] == rec[8:], (name,i,code,'original metrics')
        assert om[20+len(orec)*36:] == nm[20+len(nrec)*36:], (name,i,'kerning')
        for code in ncodes:
            node = len(nrec)//2
            for step in range(len(nrec).bit_length()+1):
                if ncodes[node] == code: break
                child = struct.unpack_from('<i',nrec[node],0 if code < ncodes[node] else 4)[0]
                assert child
                node = len(nrec)//2+child//36
            else: raise AssertionError((name,i,code,'tree lookup'))
        font_checks.append({'resource':name,'font':i,'name':font_name,'hud_original':hud_numeric,'glyphs':len(nrec),'width':nw,'height':nheight})

report = {'translated_strings':len(translations),'added_unicode_characters':len(mod['CHARS']),
          'menu_groups_complete':True,'placeholders_preserved':True,
          'race_feedback_complete':True,'hud_fonts_preserved':sum(f['hud_original'] for f in font_checks),
          'original_glyphs_and_kerning_preserved':True,'fonts':font_checks}
(root/'logs/menu-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='fonts'},ensure_ascii=False))
