#!/usr/bin/env python3
"""Generate app/theme/cyber-shell.css — the dark "cyber" skin for the classic
Command Center shell (everything inside .cy-shell).

The classic screens hard-code a light palette in three ways; this maps each
known light colour onto the cyber palette without touching any component:
  1. CSS variables from globals.css (--bg, --panel, --text, --gold, ...)
  2. Tailwind arbitrary classes (bg-[#faf9f7], text-[#999], border-[#ece8e0])
     and stock palette classes (bg-white, text-gray-500, ...)
  3. React inline styles. Server-rendered markup keeps the source spelling
     ("background:#fff"), client-rendered markup is serialised by the browser
     ("background: rgb(255, 255, 255)"), so both forms are matched.

Never themed: svg internals, images/canvas/iframes, and anything inside
.cy-keep-light (document / PDF / drawing previews that must stay on paper).

Run:  python3 scripts/gen-cyber-shell.py   (rewrites app/theme/cyber-shell.css)
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'app' / 'theme' / 'cyber-shell.css'
S = '.cy-shell'
NOT = ':not(.cy-keep-light, .cy-keep-light *, svg *)'

# ---- target palette (values of the --cy-* tokens in cyber.css) ----
T = {
    'panel':      'rgba(4, 18, 27, 0.92)',
    'panel2':     'rgba(6, 24, 36, 0.88)',
    'sunken':     'rgba(0, 10, 16, 0.75)',
    'hover':      'rgba(0, 229, 255, 0.09)',
    'sel':        'rgba(0, 229, 255, 0.12)',
    'amber_bg':   'rgba(255, 200, 87, 0.11)',
    'teal_bg':    'rgba(20, 241, 198, 0.11)',
    'mag_bg':     'rgba(255, 43, 214, 0.13)',
    'blue_bg':    'rgba(92, 200, 255, 0.11)',
    'violet_bg':  'rgba(164, 107, 255, 0.13)',
    'cyan_solid': 'rgba(0, 229, 255, 0.2)',
    'cyan_solid_h': 'rgba(0, 229, 255, 0.32)',
    'teal_solid': 'rgba(20, 241, 198, 0.2)',
    'teal_solid_h': 'rgba(20, 241, 198, 0.32)',
    'mag_solid':  'rgba(255, 43, 214, 0.24)',
    'mag_solid_h': 'rgba(255, 43, 214, 0.36)',
    'blue_solid': 'rgba(92, 200, 255, 0.22)',
    'violet_solid': 'rgba(164, 107, 255, 0.26)',
    'pink_solid': 'rgba(255, 43, 214, 0.22)',
    'grey_solid': 'rgba(127, 163, 178, 0.22)',
    'ink':        '#020a10',
    'text':       '#d9f8ff',
    'text2':      '#a9c7d3',
    'muted':      '#7fa3b2',
    'faint':      '#557a8b',
    'cyan':       '#00e5ff',
    'teal':       '#14f1c6',
    'mag':        '#ff6be3',
    'blue':       '#5cc8ff',
    'violet':     '#b98cff',
    'amber':      '#ffc857',
    'pink':       '#ff7ae6',
    'line':       'rgba(0, 229, 255, 0.2)',
    'line_soft':  'rgba(0, 229, 255, 0.12)',
    'line_cyan':  'rgba(0, 229, 255, 0.6)',
    'line_teal':  'rgba(20, 241, 198, 0.45)',
    'line_mag':   'rgba(255, 43, 214, 0.5)',
    'line_amber': 'rgba(255, 200, 87, 0.45)',
    'line_blue':  'rgba(92, 200, 255, 0.45)',
    'line_violet': 'rgba(164, 107, 255, 0.5)',
}

BG = {  # background colour -> target
    'panel':  '#fff #ffffff #fafaf8 #fafafa #fdfdfc #fefefe',
    'panel2': '#faf9f7 #f9fafb #f9f8f6 #f8f6f2 #f9f7f4 #f8fafc #f8f8f8',
    'sunken': '#f5f2ed #f5f3ef #f0ede8 #f3f4f6 #f0ece4 #eee #eeeeee #f5f5f5 #f1f5f9 #f4f4f5 #ece8e0 #e5e7eb #f0ede6 #f7f5f1 #f5f0e8',
    'sel':    '#fdf8eb #fdf9ef #fef9ec #fffdf5 #fcf8ee',
    'amber_bg': '#fef3c7 #fffbeb #fff7ed #fef9c3 #ffedd5 #fde68a',
    'teal_bg':  '#f0fdf4 #dcfce7 #ecfdf5 #d1fae5 #f0fdfa #ccfbf1',
    'mag_bg':   '#fef2f2 #fee2e2 #fff1f2 #ffe4e6 #fdf2f8 #fce7f3',
    'blue_bg':  '#eff6ff #dbeafe #f0f9ff #ecfeff #e0f2fe #cffafe',
    'violet_bg': '#faf5ff #f3e8ff #fdf4ff #ede9fe #f5f3ff',
    'cyan_solid': '#b8960c #d4af37 #b8860b #c9a50e',
    'cyan_solid_h': '#a08509 #a68500 #96750a #a3810a',
    'teal_solid': '#16a34a #22c55e #0f766e #059669 #10b981 #0d9488',
    'teal_solid_h': '#15803d #047857',
    'mag_solid': '#dc2626 #ef4444',
    'mag_solid_h': '#b91c1c',
    'blue_solid': '#2563eb #1d4ed8 #3b82f6',
    'violet_solid': '#7c3aed #6d28d9 #8b5cf6',
    'pink_solid': '#ec4899 #db2777',
}
FG = {  # text colour -> target
    'text':  '#1a1a1a #2d2a26 #1f2937 #111 #111111 #000 #000000 #333 #333333 #374151 #1a1a2e #3d2e1a #0f172a #111827 #222 #1e293b',
    'text2': '#555 #555555 #444 #444444 #525252 #4b5563 #475569 #57534e',
    'muted': '#666 #666666 #777 #777777 #888 #888888 #6b7280 #62717f #64748b #78716c',
    'faint': '#999 #999999 #9ca3af #aaa #aaaaaa #94a3b8',
    'ink':   '',
    'cyan':  '#b8960c #96750a #a68500 #a08509 #d4b84a #8a6d00 #d4af37 #b8860b #155e75 #0e7490 #06b6d4',
    'teal':  '#16a34a #15803d #166534 #22c55e #4ade80 #0f766e #047857 #065f46 #059669 #10b981',
    'mag':   '#dc2626 #991b1b #b91c1c #ef4444 #7f1d1d #9f1239 #e11d48',
    'blue':  '#2563eb #1e40af #1d4ed8 #3b82f6 #0369a1 #0284c7',
    'violet': '#7c3aed #6d28d9 #7e22ce #8b5cf6 #9333ea',
    'amber': '#d97706 #92400e #9a3412 #f59e0b #e57e22 #b45309 #c2410c #ea580c #854d0e',
    'pink':  '#ec4899 #db2777 #be185d',
}
FAINT_FG = '#bbb #bbbbbb #ccc #cccccc #ddd #dddddd #d8d3cb #c5c0b8 #d5d0c8 #c0bbb3 #e5e0d8 #d1d5db'
BORDER = {  # border colour -> target
    'line': '#ece8e0 #e5e2dc #e8e4dc #e5e0d8 #ece8e1 #ddd #dddddd #e5e7eb #d1d5db #e5e5e5 #d4d4d4 #ccc #cccccc #eee #d5d0c8 #d4cfc5 #e2e8f0 #cbd5e1 #e7e5e4 #f0ece4 #f0ede6 #f0ede8 #f5f3ef #ebe7df #e0dcd4',
    'line_cyan': '#b8960c #d4b84a #f0e6c0 #d4af37 #e8d68a #f5e6b8',
    'line_teal': '#bbf7d0 #86efac #16a34a #22c55e #a7f3d0 #0f766e',
    'line_mag': '#fecaca #fca5a5 #dc2626 #ef4444 #fda4af #ec4899 #f9a8d4',
    'line_amber': '#fde68a #fcd34d #f59e0b #fed7aa #d97706',
    'line_blue': '#bae6fd #bfdbfe #2563eb #93c5fd #06b6d4 #a5f3fc',
    'line_violet': '#7c3aed #ddd6fe #c4b5fd #e9d5ff',
}

# ---- auto-classify every other hex colour used by the shell's screens ----
import re, colorsys
ROOT = Path(__file__).resolve().parent.parent / 'app'
SCAN = [ROOT / 'CommandCenterApp.tsx', ROOT / 'components']
SKIP = ('components/ring/', 'components/amp/', 'components/public/', 'components/intake/')
def _norm(h):
    h = h.lower()
    return '#' + ''.join(c * 2 for c in h[1:]) if len(h) == 4 else h
def _hls(h):
    h = _norm(h); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hh, l, s_ = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, l, s_
def _hue_family(hue):
    if 38 <= hue < 56: return 'gold'
    if 18 <= hue < 38: return 'amber'
    if 56 <= hue < 75: return 'amber'
    if 75 <= hue < 170: return 'teal'
    if 170 <= hue < 200: return 'cyan'
    if 200 <= hue < 250: return 'blue'
    if 250 <= hue < 290: return 'violet'
    if 290 <= hue < 335: return 'pink'
    return 'mag'
HEX = r'(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b)'
CTX = {
    'bg': [r"background(?:Color)?:([^\n]*)", r"(?:bg|from|to|via)-\[" + HEX],
    'fg': [r"(?<![a-zA-Z])color:([^\n]*)", r"text-\[" + HEX],
    'bd': [r"border(?:Top|Bottom|Left|Right)?(?:Color)?:([^\n]*)", r"border(?:-[trblxy])?-\[" + HEX, r"ring-\[" + HEX],
}
used = {k: set() for k in CTX}
for base in SCAN:
    files = [base] if base.is_file() else base.rglob('*.tsx')
    for f in files:
        rel = str(f.relative_to(ROOT))
        if any(rel.startswith(x) for x in SKIP): continue
        txt = f.read_text(errors='ignore')
        for k, pats in CTX.items():
            for pat in pats:
                for m in re.finditer(pat, txt):
                    for h in re.findall(HEX, m.group(1)):
                        used[k].add(h.lower())
found = used['bg'] | used['fg'] | used['bd']
known = set()
for d in (BG, FG, BORDER):
    for v in d.values():
        known.update(_norm(x) for x in v.split())
known.update(_norm(x) for x in FAINT_FG.split())
AUTO_BG, AUTO_FG, AUTO_BD = {}, {}, {}
for h in sorted(found):
    hue, l, sat = _hls(h)
    fam = _hue_family(hue)
    neutral = sat < 0.18 or (l > 0.85 and sat < 0.45 and l < 0.955) or (l >= 0.955 and sat < 0.6)
    # background
    if l >= 0.955 and (neutral or sat < 0.6 and l >= 0.975):
        AUTO_BG[h] = 'panel' if l >= 0.985 else 'panel2'
    elif l >= 0.6 and neutral:
        AUTO_BG[h] = 'sunken'
    elif l >= 0.25 and neutral:
        AUTO_BG[h] = 'grey_solid'
    elif l >= 0.8:
        AUTO_BG[h] = {'gold': 'sel', 'amber': 'amber_bg', 'teal': 'teal_bg', 'cyan': 'blue_bg', 'blue': 'blue_bg', 'violet': 'violet_bg', 'pink': 'mag_bg', 'mag': 'mag_bg'}[fam]
    elif 0.25 <= l < 0.7 and sat >= 0.35:
        AUTO_BG[h] = {'gold': 'cyan_solid', 'amber': 'amber_bg', 'teal': 'teal_solid', 'cyan': 'cyan_solid', 'blue': 'blue_solid', 'violet': 'violet_solid', 'pink': 'pink_solid', 'mag': 'mag_solid'}[fam]
    # text
    if neutral or sat < 0.25:
        AUTO_FG[h] = 'text' if l < 0.3 else 'text2' if l < 0.42 else 'muted' if l < 0.58 else 'faint' if l < 0.92 else None
    elif l < 0.75:
        AUTO_FG[h] = {'gold': 'cyan', 'amber': 'amber', 'teal': 'teal', 'cyan': 'cyan', 'blue': 'blue', 'violet': 'violet', 'pink': 'pink', 'mag': 'mag'}[fam]
    # border
    if l >= 0.72 and (neutral or sat < 0.3):
        AUTO_BD[h] = 'line'
    elif l >= 0.6:
        AUTO_BD[h] = {'gold': 'line_cyan', 'amber': 'line_amber', 'teal': 'line_teal', 'cyan': 'line_blue', 'blue': 'line_blue', 'violet': 'line_violet', 'pink': 'line_mag', 'mag': 'line_mag'}[fam]
    elif sat >= 0.35 and l >= 0.25:
        AUTO_BD[h] = {'gold': 'line_cyan', 'amber': 'line_amber', 'teal': 'line_teal', 'cyan': 'line_cyan', 'blue': 'line_blue', 'violet': 'line_violet', 'pink': 'line_mag', 'mag': 'line_mag'}[fam]
for src, dst, ctx in ((AUTO_BG, BG, 'bg'), (AUTO_FG, FG, 'fg'), (AUTO_BD, BORDER, 'bd')):
    for h, k in src.items():
        if not k or h not in used[ctx]: continue
        if any(_norm(x) == h for v in dst.values() for x in v.split()): continue
        if dst is FG and any(_norm(x) == h for x in FAINT_FG.split()): continue
        dst[k] = (dst.get(k, '') + ' ' + h).strip()

def expand(h):
    h = h.lower()
    if len(h) == 4:
        return [h, '#' + ''.join(c * 2 for c in h[1:])]
    return [h]

def rgb(h):
    h = expand(h)[-1]
    return 'rgb(%d, %d, %d)' % (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))

def spellings(h):
    out = expand(h)
    if len(out) == 2 and out[1][1] * 6 != out[1][1:]:
        pass
    return out

def sel(attrs):
    return ',\n'.join(f'{S} [style{a}]{NOT}' for a in attrs)

def bg_attrs(h):
    a = []
    for sp in spellings(h):
        for p in ('background', 'background-color'):
            a += [f'*="{p}:{sp};" i', f'$="{p}:{sp}" i']
    for p in ('background', 'background-color'):
        a.append(f'*="{p}: {rgb(h)}"')
    return a

def fg_attrs(h):
    a = []
    for sp in spellings(h):
        a += [f'^="color:{sp};" i', f'="color:{sp}" i', f'*=";color:{sp};" i', f'$=";color:{sp}" i']
    a += [f'^="color: {rgb(h)}"', f'*="; color: {rgb(h)}"']
    return a

SIDES = ('border', 'border-top', 'border-bottom', 'border-left', 'border-right')
def border_rules(h, target):
    rules = []
    for side in SIDES:
        a = []
        prop = 'border-color' if side == 'border' else side + '-color'
        for st in ('solid', 'dashed', 'dotted'):
            for sp in spellings(h):
                a.append(f'*="{side}:" i][style*="{st} {sp}" i')
            a.append(f'*="{side}: "][style*="{st} {rgb(h)}"')
        rules.append(f'{sel(a)} {{ {prop}: {target} !important; }}')
    a = [f'*="border-color:{sp}" i' for sp in spellings(h)] + [f'*="border-color: {rgb(h)}"']
    rules.append(f'{sel(a)} {{ border-color: {target} !important; }}')
    return rules

def tw(cls):  # escape a tailwind class for a selector
    return cls.replace(':', '\\:').replace('[', '\\[').replace(']', '\\]').replace('#', '\\#').replace('/', '\\/').replace('.', '\\.')

out = []
out.append('/* GENERATED by scripts/gen-cyber-shell.py — do not edit by hand. */')
out.append('/* Dark "cyber" skin for the classic Command Center shell (.cy-shell). Visual only. */\n')

# 1. variables + base
out.append(f'''{S} {{
  --bg: #010306; --panel: rgba(3, 13, 20, 0.94); --hover: {T['hover']}; --chat-bg: transparent; --card-bg: {T['panel2']};
  --border: {T['line']}; --border-h: rgba(0, 229, 255, 0.45); --text: {T['text']}; --text-secondary: {T['text2']};
  --dim: {T['muted']}; --muted: {T['muted']}; --faint: {T['faint']};
  --gold: {T['cyan']}; --gold-light: {T['sel']}; --gold-border: {T['line_cyan']};
  --green: {T['teal']}; --green-bg: {T['teal_bg']}; --blue: {T['blue']}; --blue-bg: {T['blue_bg']};
  --red: {T['mag']}; --red-bg: {T['mag_bg']}; --orange: {T['amber']}; --orange-bg: {T['amber_bg']};
  --purple: {T['violet']}; --purple-bg: {T['violet_bg']};
  --radius: 4px; --radius-sm: 3px; --radius-lg: 6px;
  position: relative; isolation: isolate; color: var(--text); color-scheme: dark;
  background: radial-gradient(1200px 700px at 55% 20%, rgba(0, 229, 255, 0.06), transparent 65%), #010306;
}}
body:has({S}) {{ background: #010306; color-scheme: dark; }}
{S}::before {{ content: ''; position: fixed; inset: 0; pointer-events: none; z-index: -1;
  background: repeating-linear-gradient(180deg, rgba(0, 229, 255, 0.018) 0 1px, transparent 1px 3px); }}
{S} * {{ scrollbar-color: rgba(0, 229, 255, 0.35) transparent; }}
{S} ::selection {{ background: rgba(0, 229, 255, 0.35); color: #fff; }}
{S} a{NOT} {{ color: inherit; }}
''')

# 2. globals.css component classes inside the shell
out.append(f'''/* globals.css component classes */
{S} .empire-card{NOT} {{ background: {T['panel2']} !important; border: 1px solid {T['line']} !important; border-radius: 4px !important; box-shadow: none !important; color: var(--text); }}
{S} .empire-card{NOT}:hover {{ border-color: rgba(0, 229, 255, 0.45) !important; box-shadow: 0 0 16px rgba(0, 229, 255, 0.18) !important; }}
{S} .empire-card.active{NOT} {{ border-color: {T['cyan']} !important; box-shadow: 0 0 18px rgba(0, 229, 255, 0.28), inset 0 0 16px rgba(0, 229, 255, 0.08) !important; }}
{S} .status-pill {{ border-radius: 2px; letter-spacing: 0.06em; border: 1px solid currentColor; background: transparent !important; }}
{S} .status-pill.draft {{ color: {T['muted']} !important; }}
{S} .kpi-value {{ text-shadow: 0 0 12px rgba(0, 229, 255, 0.35); font-family: var(--cy-mono, ui-monospace, monospace); }}
{S} .kpi-label, {S} .section-label {{ color: {T['muted']} !important; letter-spacing: 0.14em; }}
{S} .empire-table th {{ color: {T['cyan']} !important; background: rgba(0, 229, 255, 0.05) !important; border-bottom-color: rgba(0, 229, 255, 0.4) !important; }}
{S} .empire-table td {{ border-bottom-color: {T['line_soft']} !important; color: var(--text); }}
{S} .empire-table tr:hover td {{ background: {T['hover']} !important; }}
{S} .filter-tab {{ border-radius: 2px !important; background: transparent !important; color: {T['muted']} !important; border: 1px solid {T['line']} !important; }}
{S} .filter-tab:hover {{ color: {T['cyan']} !important; border-color: rgba(0, 229, 255, 0.5) !important; }}
{S} .filter-tab.active {{ background: {T['sel']} !important; color: {T['cyan']} !important; border-color: {T['cyan']} !important; box-shadow: 0 0 12px rgba(0, 229, 255, 0.25); }}
{S} .chat-bubble-user {{ background: rgba(0, 229, 255, 0.12) !important; color: {T['text']} !important; border: 1px solid rgba(0, 229, 255, 0.35) !important; }}
{S} .chat-bubble-assistant {{ background: {T['panel2']} !important; color: {T['text']} !important; border: 1px solid {T['line']} !important; }}
{S} .form-input {{ background: {T['sunken']} !important; color: {T['text']} !important; border-color: {T['line']} !important; }}
{S} .form-input:focus {{ border-color: {T['cyan']} !important; box-shadow: 0 0 0 1px {T['cyan']}, 0 0 12px rgba(0, 229, 255, 0.25) !important; }}
''')

# 3. form controls + tables + prose
out.append(f'''/* native controls */
{S} :is(input:not([type=checkbox], [type=radio], [type=range], [type=color], [type=file], [type=submit], [type=button]), select, textarea){NOT} {{
  background-color: {T['sunken']} !important; color: {T['text']} !important; border-color: {T['line']} !important; caret-color: {T['cyan']}; }}
{S} :is(input, select, textarea){NOT}:focus {{ border-color: {T['cyan']} !important; outline: none; box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.6), 0 0 12px rgba(0, 229, 255, 0.22) !important; }}
{S} :is(input, textarea)::placeholder {{ color: {T['faint']} !important; opacity: 1; }}
{S} select option {{ background: #04121b; color: {T['text']}; }}
{S} input[type=checkbox], {S} input[type=radio], {S} input[type=range] {{ accent-color: {T['cyan']}; }}
{S} table{NOT} th {{ color: {T['cyan']}; border-color: rgba(0, 229, 255, 0.3); }}
{S} table{NOT} td {{ border-color: {T['line_soft']}; }}
{S} :is(hr){NOT} {{ border-color: {T['line']}; }}
{S} :is(code, pre){NOT} {{ background: rgba(0, 229, 255, 0.07) !important; color: #bff6ff !important; border-color: {T['line']} !important; }}
{S} :is(h1, h2, h3){NOT} {{ text-shadow: 0 0 10px rgba(0, 229, 255, 0.18); }}
''')

# 4. tailwind classes
def fg_target(h):
    h6 = expand(h)[-1]
    for k, v in FG.items():
        if any(expand(x)[-1] == h6 for x in v.split()):
            return T[k]
    if any(expand(x)[-1] == h6 for x in FAINT_FG.split()):
        return T['faint']
    return None
def bg_target(h):
    h6 = expand(h)[-1]
    for k, v in BG.items():
        if any(expand(x)[-1] == h6 for x in v.split()):
            return T[k]
    return None
def bd_target(h):
    h6 = expand(h)[-1]
    for k, v in BORDER.items():
        if any(expand(x)[-1] == h6 for x in v.split()):
            return T[k]
    return None

allhex = set()
for d in (BG, FG, BORDER):
    for v in d.values():
        allhex.update(x.lower() for x in v.split())
allhex.update(x.lower() for x in FAINT_FG.split())
hexes = sorted({expand(h)[0] for h in allhex if h})

from collections import defaultdict
def group(rules_by_target, prop, extra=''):
    for t, items in rules_by_target.items():
        if items:
            out.append(f'{S} :is({", ".join(items)}){NOT}{extra} {{ {prop}: {t} !important; }}')

out.append('/* tailwind arbitrary colour classes */')
for pre, state in (('', ''), ('hover:', ':hover'), ('focus:', ':focus')):
    bgc, fgc, bdc = defaultdict(list), defaultdict(list), defaultdict(list)
    for h in hexes:
        for sp in spellings(h):
            t = bg_target(h)
            if t: bgc[t].append('.' + tw(pre + 'bg-[' + sp + ']'))
            t = fg_target(h)
            if t: fgc[t].append('.' + tw(pre + 'text-[' + sp + ']'))
            t = bd_target(h)
            if t: bdc[t].append('.' + tw(pre + 'border-[' + sp + ']'))
    group(bgc, 'background-color', state); group(fgc, 'color', state); group(bdc, 'border-color', state)
rc = defaultdict(list)
for h in hexes:
    t = bd_target(h)
    if t:
        rc[t] += ['.' + tw('ring-[' + sp + ']') for sp in spellings(h)]
group(rc, '--tw-ring-color')
out.append(f'{S} :is(.text-\\[\\#2D2A26\\], .hover\\:text-\\[\\#2D2A26\\]:hover){NOT} {{ color: {T["text"]} !important; }}')

PALETTE = {
    'bg-white': ('background-color', T['panel']), 'hover:bg-white': ('background-color', T['hover']),
    'bg-gray-50': ('background-color', T['panel2']), 'hover:bg-gray-50': ('background-color', T['hover']),
    'bg-gray-100': ('background-color', T['sunken']), 'hover:bg-gray-200': ('background-color', T['hover']),
    'bg-slate-50': ('background-color', T['panel2']), 'hover:bg-slate-50': ('background-color', T['hover']),
    'bg-slate-100': ('background-color', T['sunken']), 'bg-slate-900': ('background-color', '#000'),
    'bg-red-50': ('background-color', T['mag_bg']), 'hover:bg-red-50': ('background-color', T['mag_bg']),
    'bg-amber-50': ('background-color', T['amber_bg']), 'bg-amber-100': ('background-color', T['amber_bg']),
    'bg-emerald-50': ('background-color', T['teal_bg']), 'bg-emerald-100': ('background-color', T['teal_bg']),
    'bg-teal-100': ('background-color', T['teal_bg']), 'bg-blue-50': ('background-color', T['blue_bg']),
    'bg-purple-50': ('background-color', T['violet_bg']), 'bg-orange-50': ('background-color', T['amber_bg']),
    'bg-teal-600': ('background-color', T['teal_solid']), 'bg-emerald-600': ('background-color', T['teal_solid']),
    'bg-red-600': ('background-color', T['mag_solid']), 'hover:bg-red-700': ('background-color', T['mag_solid_h']),
    'text-gray-900': ('color', T['text']), 'text-gray-700': ('color', T['text2']), 'text-gray-600': ('color', T['muted']),
    'text-gray-500': ('color', T['muted']), 'text-gray-400': ('color', T['faint']),
    'text-slate-950': ('color', T['text']), 'text-slate-900': ('color', T['text']), 'text-slate-800': ('color', T['text']),
    'text-slate-700': ('color', T['text2']), 'text-slate-600': ('color', T['muted']), 'text-slate-500': ('color', T['muted']),
    'text-red-500': ('color', T['mag']), 'text-red-600': ('color', T['mag']), 'text-red-700': ('color', T['mag']), 'text-red-800': ('color', T['mag']),
    'hover:text-red-500': ('color', T['mag']),
    'text-amber-700': ('color', T['amber']), 'text-amber-800': ('color', T['amber']), 'text-amber-900': ('color', T['amber']),
    'text-emerald-700': ('color', T['teal']), 'text-emerald-800': ('color', T['teal']), 'text-teal-700': ('color', T['teal']),
    'text-teal-800': ('color', T['teal']), 'text-green-600': ('color', T['teal']), 'text-blue-600': ('color', T['blue']),
    'text-purple-600': ('color', T['violet']), 'text-orange-600': ('color', T['amber']),
    'border-slate-100': ('border-color', T['line_soft']), 'border-slate-200': ('border-color', T['line']), 'border-slate-300': ('border-color', T['line']),
    'border-gray-100': ('border-color', T['line_soft']), 'border-gray-200': ('border-color', T['line']), 'border-gray-300': ('border-color', T['line']),
    'border-red-200': ('border-color', T['line_mag']), 'border-red-300': ('border-color', T['line_mag']),
    'border-amber-200': ('border-color', T['line_amber']), 'border-emerald-200': ('border-color', T['line_teal']),
    'border-teal-500': ('border-color', T['line_teal']), 'border-teal-600': ('border-color', T['line_teal']),
}
out.append('/* tailwind palette classes */')
for cls, (prop, val) in PALETTE.items():
    state = ':hover' if cls.startswith('hover:') else ''
    out.append(f'{S} .{tw(cls)}{NOT}{state} {{ {prop}: {val} !important; }}')

# 5. inline styles, grouped by target colour
out.append('/* inline style colours (SSR spelling + browser-serialised rgb) */')
bgi, fgi = defaultdict(list), defaultdict(list)
for h in hexes:
    t = bg_target(h)
    if t: bgi[t] += [f'[style{a}]' for a in bg_attrs(h)]
    t = fg_target(h)
    if t: fgi[t] += [f'[style{a}]' for a in fg_attrs(h)]
group(bgi, 'background-color'); group(fgi, 'color')

def bd_any(h):
    a = []
    for st in ('solid', 'dashed'):
        a += [f'[style*="{st} {sp}" i]' for sp in spellings(h)] + [f'[style*="{st} {rgb(h)}"]']
    a += [f'[style*="border-color:{sp}" i]' for sp in spellings(h)] + [f'[style*="border-color: {rgb(h)}"]']
    return a
# accents first, neutral lines last (an element mixing both ends up all-neutral) ...
acc, neu = defaultdict(list), defaultdict(list)
for h in hexes:
    t = bd_target(h)
    if not t: continue
    (neu if t in (T['line'],) else acc)[t] += bd_any(h)
group(acc, 'border-color'); group(neu, 'border-color')
# ... then accent stripes on the left / top edge win back their colour.
for side in ('border-left', 'border-top'):
    sa = defaultdict(list)
    for h in hexes:
        t = bd_target(h)
        if not t or t == T['line']: continue
        for st in ('solid',):
            sa[t] += [f'[style*="{side}:" i][style*="{st} {sp}" i]' for sp in spellings(h)] + [f'[style*="{side}: "][style*="{st} {rgb(h)}"]']
    group(sa, side + '-color')

# light gradients -> flat dark tint; gold gradients -> cyan
out.append('/* gradients */')
gr = defaultdict(list)
for h in hexes:
    if _norm(h) in ('#ffffff',): continue
    t = bg_target(h)
    if not t: continue
    gr[t] += [f'[style*="gradient("][style*="{sp}" i]' for sp in spellings(h)] + [f'[style*="gradient("][style*="{rgb(h)}"]']
for t, items in gr.items():
    if t in (T['cyan_solid'], T['cyan_solid_h']):
        continue
    out.append(f'{S} :is({", ".join(items)}){NOT} {{ background: {t} !important; }}')
gold = ['#b8960c', '#d4af37', '#b8860b', '#c9a50e', '#a08509']
gi = []
for h in gold:
    gi += [f'[style*="gradient("][style*="{h}" i]', f'[style*="gradient("][style*="{rgb(h)}"]']
out.append(f'{S} :is({", ".join(gi)}){NOT} {{ background: linear-gradient(135deg, rgba(0, 229, 255, 0.85), rgba(0, 150, 190, 0.85)) !important; color: #001018 !important; box-shadow: 0 0 18px rgba(0, 229, 255, 0.35) !important; }}')
wa = ['[style*="background:white" i]', '[style*="background: white"]', '[style*="background-color:white" i]', '[style*="background-color: white"]']
out.append(f'{S} :is({", ".join(wa)}){NOT} {{ background-color: {T["panel"]} !important; }}')

# 6. gold-tinted rgba glows -> cyan
out.append(f'''/* gold glows -> cyan */
{S} [style*="rgba(184,150,12" i]{NOT}, {S} [style*="rgba(184, 150, 12"]{NOT} {{ --cy-gold-glow: 1; }}
{S} [style*="box-shadow"][style*="rgba(184, 150, 12"]{NOT}, {S} [style*="box-shadow:"][style*="rgba(184,150,12"]{NOT} {{ box-shadow: 0 0 14px rgba(0, 229, 255, 0.28) !important; }}
{S} :is([style*="background: rgba(184, 150, 12"], [style*="background:rgba(184,150,12"], [style*="background-color: rgba(184, 150, 12"]){NOT} {{ background-color: {T['sel']} !important; }}
{S} :is([style*="solid rgba(184, 150, 12"], [style*="solid rgba(184,150,12"]){NOT} {{ border-color: {T['line_cyan']} !important; }}
''')

# 7. never theme media
out.append(f'''/* media stays as-is */
{S} :is(img, video, canvas, iframe, picture) {{ filter: none !important; }}
{S} .cy-keep-light {{ color-scheme: light; color: #1a1a1a; }}
''')

OUT.write_text('\n'.join(out) + '\n')
print(f'wrote {OUT} ({OUT.stat().st_size // 1024} KB)')
