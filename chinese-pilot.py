"""Small, reversible RSC2 menu translation/font-atlas experiment."""
from pathlib import Path
import io, json, math, os, shutil, struct, zlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'RalliSport2'
OUTPUT = ROOT / 'rsc2-zh-pilot'
TRANSLATIONS = {
    'LID_HEAD_MAIN': '主菜单',
    'LID_HEAD_OPTIONS': '设置',
    'LID_HEAD_SELECT_PROFILE': '选择档案',
    'LID_B_BACK': '返回',
    'LID_B_CANCEL': '取消',
    'LID_CHOICE_START_GAME': '开始游戏',
    'LID_CHOICE_CREATE_PROFILE': '创建新档案',
    'LID_CHOICE_OPTIONS': '设置',
}
if (ROOT / 'menu-zh.json').exists():
    TRANSLATIONS = json.loads((ROOT / 'menu-zh.json').read_text(encoding='utf-8'))
if (ROOT / 'menu-race-feedback-zh.json').exists():
    feedback = json.loads((ROOT / 'menu-race-feedback-zh.json').read_text(encoding='utf-8'))
    assert not TRANSLATIONS.keys() & feedback.keys(), 'Duplicate translation keys'
    TRANSLATIONS.update(feedback)
CHARS = sorted({c for text in TRANSLATIONS.values() for c in text if ord(c) >= 128})
ENCODING = {c: ord(c) for c in CHARS}

def parse_locale(b):
    count = struct.unpack_from('<I', b, 32)[0]
    start = 36 + (count + 1) * 6
    pairs = [struct.unpack_from('<HI', b, 36 + i * 6) for i in range(count)]
    values = {}
    for key, offset in pairs:
        a = start + offset * 2
        z = a
        while b[z:z+2] != b'\0\0': z += 2
        values[key] = b[a:z].decode('utf-16le')
    end = struct.unpack_from('<I', b, 16)[0]
    n = struct.unpack_from('<I', b, end + 4)[0]
    names_base = end + 8 + n * 8
    names = {}
    for i in range(n):
        key, _, offset = struct.unpack_from('<HHI', b, end + 8 + i * 8)
        a = names_base + offset
        names[b[a:b.index(0, a)].decode('ascii')] = key
    return pairs, values, names, end

def translate_locale(b):
    pairs, values, names, old_end = parse_locale(b)
    updates = {}
    for name, text in TRANSLATIONS.items():
        assert name in names, name
        updates[names[name]] = text
    string_data, table = bytearray(), bytearray()
    for key, _ in pairs:
        table += struct.pack('<HI', key, len(string_data) // 2)
        string_data += updates.get(key, values[key]).encode('utf-16le') + b'\0\0'
    table += struct.pack('<HI', 0xFFFF, len(string_data) // 2)
    block = struct.pack('<II', 8 + len(table) + len(string_data), len(pairs)) + table + string_data
    delta = len(block) - (old_end - 28)
    head = bytearray(b[:28])
    for off in (16, 20, 24):
        struct.pack_into('<I', head, off, struct.unpack_from('<I', head, off)[0] + delta)
    result = bytes(head) + block + b[old_end:]
    _, check, _, new_end = parse_locale(result)
    assert result[new_end:] == b[old_end:]
    for key in values: assert check[key] == updates.get(key, values[key])
    return result

def unpack_fonts(b):
    index = zlib.decompress(b[8:])
    # The two English font resources, following four fixed directory records.
    entries = []
    for pos in (136, 200):
        off, size, first, count = struct.unpack_from('<IIHH', index, pos + 8)
        name = index[pos+20:pos+64].split(b'\0')[0].decode('ascii')
        raw = bytearray(size)
        for i in range(first, first + count):
            comp, length, c_off, r_off = struct.unpack_from('<4I', index, 264 + i * 16)
            chunk = zlib.decompress(b[2048+off+c_off:2048+off+c_off+comp])
            assert len(chunk) == length
            raw[r_off:r_off+length] = chunk
        entries.append((pos, name, bytes(raw)))
    return index, entries

def align(b, n=128):
    b.extend(bytes((-len(b)) % n))

def patch_resource(b, name):
    _, nt, nf, table, font_table, data_base = struct.unpack_from('<6I', b)
    assert nt == nf
    header = bytearray(b[:data_base])
    payload = bytearray()
    changed = []
    for i in range(nt):
        te, fe = table + i * 136, font_table + i * 188
        off, length = struct.unpack_from('<II', b, te + 128)
        metrics = bytearray(b[data_base+off:data_base+off+length])
        version, width, height, size, count = struct.unpack_from('<5I', metrics)
        texture_off = struct.unpack_from('<I', b, fe + 128)[0]
        fmt = struct.unpack_from('<I', b, fe + 144)[0]
        assert (fmt >> 8) & 255 == 0x13, hex(fmt)  # linear A8, pitch is width
        packed_size = struct.unpack_from('<I', b, fe + 148)[0]
        pitch = ((packed_size >> 24) + 1) * 64
        raw_texture = b[data_base+texture_off:data_base+texture_off+pitch*height]
        assert len(raw_texture) == pitch*height
        atlas = Image.frombytes('L', (width, height), raw_texture, 'raw', 'L', pitch, 1)
        records = {struct.unpack_from('<I', metrics, 20 + j * 36 + 32)[0]:
                   bytearray(metrics[20+j*36:20+(j+1)*36]) for j in range(count)}
        font_name = b[fe:fe+128].split(b'\0')[0].decode('ascii')
        # The instrument renderer also accesses these glyphs by numeric
        # index. Preserve both complete HUD fonts, including their tree,
        # record count, atlas dimensions and digit layout.
        hud_numeric = font_name.endswith(('/rpmfont_12', '/rpmfont_24'))
        added = [] if hud_numeric else [ch for ch in CHARS if ord(ch) not in records]
        if added:
            cell = size + 4
            old_width, old_height = width, height
            width = max(512, width)
            while height + 4 + math.ceil(len(added) / (width // cell)) * cell > 2048:
                width *= 2
            cols = width // cell
            rows = math.ceil(len(added) / cols)
            new_height = height + 4 + rows * cell
            assert width <= 4096 and new_height <= 4096
            expanded = Image.new('L', (width, new_height))
            expanded.paste(atlas, (0, 0))
            font = ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', size * 4)
            for j, ch in enumerate(added):
                bb = font.getbbox(ch)
                # Keep punctuation on a normal em square. Cropping each
                # glyph to its ink bounds stretched commas to full height.
                pixels = size * 4
                glyph = Image.new('L', (pixels, pixels))
                top = font.getbbox('国')[1]
                dy = min(-top, pixels-bb[3])
                ImageDraw.Draw(glyph).text((0, dy), ch, font=font, fill=255)
                glyph = glyph.resize((size, size), Image.Resampling.LANCZOS)
                x, y = (j % cols) * cell + 2, height + 6 + (j // cols) * cell
                expanded.paste(glyph, (x, y))
                record = bytearray(36)
                struct.pack_into('<3f4H2I', record, 8, 0., float(size+1), 0., x, y, x+size, y+size, size, ord(ch))
                records[ord(ch)] = record
            assert expanded.crop((0, 0, old_width, old_height)).tobytes() == atlas.tobytes()
            atlas = expanded
            # DIFB stores a balanced search tree with both child offsets
            # relative to the middle record, rather than to each node.
            codes = sorted(records)
            def link(lo, hi):
                if lo == hi: return None
                mid = (lo + hi) // 2
                left, right = link(lo, mid), link(mid+1, hi)
                offsets = [0 if child is None else (child-len(codes)//2)*36 for child in (left, right)]
                struct.pack_into('<2i', records[codes[mid]], 0, *offsets)
                return mid
            link(0, len(codes))
            tail = metrics[20+count*36:]
            metrics = bytearray(struct.pack('<5I', version, width, new_height, size, len(codes)))
            metrics += b''.join(records[code] for code in codes) + tail
            for code in codes:
                node = len(codes)//2
                while codes[node] != code:
                    child = struct.unpack_from('<i', records[codes[node]], 0 if code < codes[node] else 4)[0]
                    assert child, (name, code)
                    node = len(codes)//2 + child//36
            packed = ((width//64-1) << 24) | ((new_height-1) << 12) | (width-1)
            struct.pack_into('<I', header, fe + 148, packed)
            struct.pack_into('<I', header, fe + 168, width)
            struct.pack_into('<I', header, fe + 172, new_height)
            changed.append(header[fe:fe+128].split(b'\0')[0].decode('ascii'))
            atlas.save(ROOT / 'font-probe' / (name + '-' + str(i) + '-zh.png'))
        align(payload)
        struct.pack_into('<II', header, te + 128, len(payload), len(metrics))
        payload += metrics
        align(payload)
        struct.pack_into('<I', header, fe + 128, len(payload))
        # rpmfont_24 has a logical width of 125 but a 128-byte row pitch.
        # Retain its complete original padded texture, including the tail.
        payload += raw_texture if hud_numeric else atlas.tobytes()
    align(payload, 2048)
    return bytes(header + payload), changed

def repack_fonts(original):
    index, entries = unpack_fonts(original)
    new_index = bytearray(index[:264])
    tables, data, expected, changed = bytearray(), bytearray(), {}, []
    chunk_count = 0
    for pos, name, resource in entries:
        raw, fonts = patch_resource(resource, name)
        expected[name] = raw
        changed += fonts
        align(data, 2048)
        base = len(data)
        first = chunk_count
        for ro in range(0, len(raw), 0x20000):
            block = raw[ro:ro+0x20000]
            comp = zlib.compress(block, 9)
            align(data, 2048)
            tables += struct.pack('<4I', len(comp), len(block), len(data) - base, ro)
            data += comp
            chunk_count += 1
        struct.pack_into('<IIHH', new_index, pos + 8, base, len(raw), first, chunk_count - first)
    struct.pack_into('<H', new_index, 6, chunk_count)
    comp_index = zlib.compress(new_index + tables, 9)
    assert len(comp_index) + 8 < 2048
    result = bytearray(struct.pack('<II', len(comp_index), 2048) + comp_index)
    align(result, 2048)
    result += data
    align(result, 2048)
    _, check = unpack_fonts(result)
    for _, name, raw in check: assert raw == expected[name]
    return bytes(result), changed

def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'portable-mode.txt').write_text('Per-install cache and settings.\n', encoding='ascii')
    settings = OUTPUT / 'portable-data' / 'Settings'
    settings.mkdir(parents=True, exist_ok=True)
    english_settings = Path(r'D:\Games\RalliSport Challenge 2\英文版\portable-data\Settings\settings.ini')
    if not (settings / 'settings.ini').exists() and english_settings.exists():
        shutil.copy2(english_settings, settings / 'settings.ini')
    game = OUTPUT / 'game'
    game.mkdir(exist_ok=True)
    locale = Path('Locale/English/localestrings.str')
    fonts = Path('Layer0/FontsEnglish.fa')
    for src in ORIGINAL.rglob('*'):
        rel = src.relative_to(ORIGINAL)
        dst = game / rel
        if src.is_dir(): dst.mkdir(parents=True, exist_ok=True)
        elif rel not in (locale, fonts) and not dst.exists():
            os.link(src, dst)  # unchanged disc assets, same C: volume
    for name in ('rsc2.exe',):
        shutil.copy2(Path(r'D:\Games\RalliSport Challenge 2\英文版') / name, OUTPUT / name)
    translated = translate_locale((ORIGINAL / locale).read_bytes())
    exit_assets = ROOT / 'menu-exit-assets.py'
    if exit_assets.exists():
        import runpy
        native_exit = runpy.run_path(str(exit_assets))
        translated = native_exit['locale'](translated, True, parse_locale)
        menu_archive, _ = native_exit['patch_archive']((ORIGINAL / 'Layer0/MenuHDD.fa').read_bytes())
        # Replace the path atomically: unchanged pilot assets can be hardlinks
        # to the original disc and must never be overwritten in place.
        menu_path = game / 'Layer0/MenuHDD.fa'
        temporary = menu_path.with_suffix('.new')
        temporary.write_bytes(menu_archive)
        os.replace(temporary, menu_path)
    (game / locale).write_bytes(translated)
    packed, changed = repack_fonts((ORIGINAL / fonts).read_bytes())
    (game / fonts).write_bytes(packed)
    report = dict(translations=TRANSLATIONS, font_mode='unicode', unicode_glyphs={c:hex(v) for c,v in ENCODING.items()},
                  patched_fonts=changed, output=str(OUTPUT), font_bytes=len(packed))
    (OUTPUT / 'pilot-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
