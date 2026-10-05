#!/usr/bin/env python3
"""Generate app/theme/gold-docs.generated.css: a COLOR-ONLY override of the cyber theme that
maps every color in the cyber/docs/ring stylesheets onto the gold-standard client-doc palette.

Palette source (do not guess; these are the PDF templates):
  backend/app/services/drawing/max_sheet_chrome.py  PAPER #f7f3ea, INK #20241f, GOLD #b8912f,
      BAND #16191c, HAIR #cdc4b0, MUTE #7b7466, CREAM_TEXT #f4efe2, MUTE_BAND #a49b88, #fbf8f1
  backend/app/services/estimates/mclean_estimate_pdf.py  PANEL #efe9dc, ROW_SHADE #efe8dc
  presentation (EST-2026-297 rev M) band #2c2416 (sampled from the rendered PDF)
Derived (needed for WCAG AA text on paper, not present in the PDFs): GOLD_T, MUTE_T, INK2, status hues.

Every rule is re-emitted under html[data-theme="gold"], so it only applies when the gold preview
is switched on (?theme=gold). Only color values change; no other property is emitted.
Run with a python that has tinycss2 (backend/venv).
"""
import colorsys, re, sys
from pathlib import Path
import tinycss2

APP = Path(__file__).resolve().parents[1] / 'app'
SOURCES = ['theme/cyber.css', 'theme/cyber-shell.css', 'theme/cyber-layout.css', 'theme/cyber-pages.css',
           'theme/cyber-hud.css', 'theme/cyber-calm.css', 'components/docs/docs.css', 'components/ring/ring.css']
P = dict(PAPER=(0xf7, 0xf3, 0xea), CARD=(0xfb, 0xf8, 0xf1), PANEL=(0xef, 0xe9, 0xdc), HAIR=(0xcd, 0xc4, 0xb0),
         BAND=(0x16, 0x19, 0x1c), INK=(0x20, 0x24, 0x1f), INK2=(0x3d, 0x3a, 0x33), MUTE_T=(0x6b, 0x64, 0x57),
         GOLD=(0xb8, 0x91, 0x2f), GOLD_T=(0x7d, 0x5f, 0x17))
ACC = {  # family: (text-safe, base)
    'gold': (P['GOLD_T'], P['GOLD']),
    'green': ((0x2f, 0x6b, 0x45), (0x3f, 0x8a, 0x5a)),
    'red': ((0x9e, 0x2f, 0x2f), (0xb2, 0x3b, 0x3b)),
    'amber': ((0x8f, 0x4a, 0x12), (0xc8, 0x69, 0x1c)),
    'blue': ((0x2c, 0x5a, 0x85), (0x3b, 0x6e, 0xa5)),
    'plum': ((0x5e, 0x45, 0x90), (0x7a, 0x5b, 0xb0)),
}
NAMED = {'white': (255, 255, 255, 1.0), 'black': (0, 0, 0, 1.0), '#fff': (255, 255, 255, 1.0)}

def parse_color(tok):
    if tok.type == 'hash':
        h = tok.value
        if len(h) in (3, 4): h = ''.join(c * 2 for c in h)
        if len(h) not in (6, 8) or not re.fullmatch(r'[0-9a-fA-F]+', h): return None
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b, a)
    if tok.type == 'function' and tok.lower_name in ('rgb', 'rgba'):
        nums = [t for t in tok.arguments if t.type in ('number', 'percentage')]
        if len(nums) < 3: return None
        def ch(t): return t.value * 2.55 if t.type == 'percentage' else t.value
        r, g, b = (ch(t) for t in nums[:3])
        a = (nums[3].value / 100 if nums[3].type == 'percentage' else nums[3].value) if len(nums) > 3 else 1.0
        return (r, g, b, a)
    if tok.type == 'ident' and tok.lower_value in ('white', 'black'):
        return NAMED[tok.lower_value]
    return None

def family(r, g, b):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s < 0.45 or l < 0.25 or l > 0.9: return None, l
    deg = h * 360
    if 175 <= deg < 200: return 'gold', l          # cyan -> gold accent
    if 200 <= deg < 235: return 'blue', l
    if 235 <= deg < 290: return 'plum', l
    if 290 <= deg < 345: return 'red', l           # magenta = alert/overdue
    if deg >= 345 or deg < 18: return 'red', l
    if 18 <= deg < 70: return 'amber', l
    if 70 <= deg < 175: return 'green', l          # teal/green = ok/paid
    return None, l

def fmt(rgb, a):
    r, g, b = (int(round(x)) for x in rgb)
    if a >= 0.999: return '#%02x%02x%02x' % (r, g, b)
    return 'rgba(%d, %d, %d, %s)' % (r, g, b, ('%.3f' % a).rstrip('0').rstrip('.'))

def map_color(c, role):
    r, g, b, a = c
    fam, l = family(r, g, b)
    if fam:
        txt, base = ACC[fam]
        if role == 'text': return fmt(txt, max(a, 0.9) if a > 0.5 else a)
        if role == 'tshadow': return 'transparent'
        if role == 'shadow': return fmt(base, a * 0.35)
        return fmt(base, a)
    # neutrals
    if role == 'text':
        if l >= 0.8: return fmt(P['INK'], a)
        if l >= 0.6: return fmt(P['INK2'], a)
        if l >= 0.3: return fmt(P['MUTE_T'], a)
        return fmt(P['BAND'], a)
    if role == 'bg':
        if l > 0.6: return fmt((32, 36, 31), a) if a < 0.3 else fmt((r, g, b), a)  # light overlays invert, opaque light stays
        if l < 0.03: return fmt(P['PAPER'], a)
        if l < 0.09: return fmt(P['CARD'], a)
        if l < 0.35: return fmt(P['PANEL'], a)
        return fmt(P['HAIR'], a)
    if role == 'border':
        return fmt(P['HAIR'], max(a, 0.75) if a > 0.04 else a)
    if role == 'tshadow': return 'transparent'
    if role == 'shadow':
        if l < 0.3: return fmt(P['INK'], min(a, 0.14))
        return 'transparent'
    if role == 'fill':
        if l >= 0.6: return fmt(P['INK'], a)
        if l < 0.35: return fmt(P['PANEL'], a)
        return fmt(P['HAIR'], a)
    return None

def role_for(prop):
    p = prop.lower()
    if p.startswith('--'):
        if re.search(r'(text|muted|dim|faint|secondary|ink)', p): return 'text'
        if re.search(r'(-bg|bg$|^--bg|panel|card|hover|chat|surface|paper)', p): return 'bg'
        if re.search(r'(border|line|rule|hair)', p): return 'border'
        if re.search(r'(glow|shadow)', p): return 'shadow'
        return 'text'   # accent vars (--gold, --cy-cyan, --rg-teal...) are mostly used as text/icon color
    if p in ('color', 'caret-color', '-webkit-text-fill-color', 'text-decoration-color', 'accent-color'): return 'text'
    if p.startswith('background'): return 'bg'
    if p.startswith(('border', 'outline', 'column-rule')) or p == 'stroke': return 'border'
    if p == 'text-shadow': return 'tshadow'   # neon text glow has no place on paper
    if p in ('box-shadow', 'filter', '-webkit-filter'): return 'shadow'
    if p in ('fill', 'stop-color', 'flood-color'): return 'fill'
    return None

def transform_tokens(tokens, role):
    changed = False; out = []
    for t in tokens:
        c = parse_color(t)
        if c is not None:
            m = map_color(c, role)
            if m:
                out.append(m); changed = True; continue
        if t.type == 'function' and t.lower_name not in ('rgb', 'rgba', 'url', 'var'):
            inner, ch = transform_tokens(t.arguments, role)
            if ch:
                out.append(f'{t.name}({inner})'); changed = True; continue
        out.append(tinycss2.serialize([t]))
    return ''.join(out), changed

PFX = 'html[data-theme="gold"]'
def prefix_selector(sel):
    parts, groups, cur = [], [], []
    for t in sel:  # split on top-level commas only (keeps :is(a, b) and [style*="rgb(0, 229, 255)"] intact)
        if t.type == 'literal' and t.value == ',': groups.append(cur); cur = []
        else: cur.append(t)
    groups.append(cur)
    for g in groups:
        s = tinycss2.serialize(g).strip()
        if not s: continue
        if s.startswith(':root'): parts.append(PFX + s[5:])
        elif re.match(r'html\b', s): parts.append(PFX + s[4:])
        else: parts.append(f'{PFX} {s}')
    return ', '.join(parts)

def process(rules, depth=0):
    out = []
    for r in rules:
        if r.type == 'qualified-rule':
            decls = tinycss2.parse_declaration_list(r.content, skip_whitespace=True, skip_comments=True)
            body = []
            for d in decls:
                if d.type != 'declaration': continue
                role = role_for(d.name)
                if not role: continue
                val, ch = transform_tokens(d.value, role)
                if ch:
                    body.append(f'{d.name}: {val.strip()}{" !important" if d.important else ""};')
            if body:
                out.append(f'{prefix_selector(r.prelude)} {{ ' + ' '.join(body) + ' }')
        elif r.type == 'at-rule' and r.lower_at_keyword in ('media', 'supports') and r.content:
            inner = process(tinycss2.parse_rule_list(r.content, skip_whitespace=True, skip_comments=True), depth + 1)
            if inner:
                out.append(f'@{r.at_keyword} {tinycss2.serialize(r.prelude).strip()} {{\n' + '\n'.join(inner) + '\n}')
    return out

def main():
    chunks = ['/* GENERATED by scripts/gen_gold_theme.py from the cyber/docs/ring stylesheets. Do not edit by hand.\n'
              '   Color-only overrides, active only under html[data-theme="gold"] (gold-standard client-doc palette). */']
    n = 0
    for rel in SOURCES:
        src = (APP / rel).read_text()
        rules = tinycss2.parse_stylesheet(src, skip_whitespace=True, skip_comments=True)
        res = process(rules); n += len(res)
        chunks.append(f'\n/* ---- from {rel} ({len(res)} rules) ---- */\n' + '\n'.join(res))
    (APP / 'theme' / 'gold-docs.generated.css').write_text('\n'.join(chunks) + '\n')
    print('rules', n)

if __name__ == '__main__':
    main()
