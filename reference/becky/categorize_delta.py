"""D42 delta characterisation.

Strategy:
1. Normalise each text: collapse all runs of whitespace into a single space.
   This removes leading-space / column-position drift caused by glyph-width
   changes (italic -> non-italic).
2. Compare normalised streams line-by-line.
3. Classify each differing line:
     A. PHOTOS: contains photo-caption content or the "NO SITE PHOTO ON FILE"
        placeholder.
     B. WHITESPACE_ONLY_AFTER_NORMALISE: line stripped of all whitespace
        (squeeze + lower) is identical to its counterpart.
     C. UNEXPLAINED: real content difference not in A.
4. Report counts.
"""
import re, sys

WS = re.compile(r"\s+")

def norm_lines(p):
    out = []
    with open(p, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            out.append(WS.sub(" ", ln).strip())
    return out

def norm_strong(p):
    """Lowercase + squeeze + strip per line; return list of strings."""
    return [s.lower() for s in norm_lines(p)]

REF = "/tmp/d42/audit/ref_raw.txt"
BASE = "/tmp/d42/baseline/base_raw.txt"
REF_LAYOUT = "/tmp/d42/audit/reference_text.txt"
BASE_LAYOUT = "/tmp/d42/baseline/baseline_text.txt"

ref_layout = norm_lines(REF_LAYOUT)
base_layout = norm_lines(BASE_LAYOUT)
ref_raw = norm_lines(REF)
base_raw = norm_lines(BASE)

print("=== layout-normalised line counts ===")
print(f"  reference: {len(ref_layout)} lines")
print(f"  baseline:  {len(base_layout)} lines")

ref_strong = norm_strong(REF_LAYOUT)
base_strong = norm_strong(BASE_LAYOUT)

# Diff in layout-normalised space
def diff_lines(a, b):
    return list(__import__("difflib").ndiff(a, b))

d = diff_lines(ref_layout, base_layout)

PHOTOS_KEYWORDS = (
    "window wall from the room",
    "bay from the room",
    "mantel wall",
    "balcony doors",
    "3 units",
    "right wall - triple unit",
    "fireplace wall - two windows each side",
    "two window units and the transomed",
    "panelled office",
    "existing balloon shade",
    "no site photo on file",
    "return",  # 'curved return' caption
    "triple unit",  # 'RIGHT WALL - triple unit' caption
    "fireplace",  # 'Fireplace wall' (when standalone caption)
)

categories = {"A_PHOTOS": [], "B_WHITESPACE_GLYPH": [], "C_UNEXPLAINED": []}

# Walk paired < > hunks
i = 0
while i < len(d):
    line = d[i]
    if line.startswith("  "):
        i += 1
        continue
    if line.startswith("- "):
        ref_line = line[2:]
        # find matching > line (if any) within next few
        j = i + 1
        base_line = None
        while j < len(d) and d[j].startswith("? "):
            j += 1
        if j < len(d) and d[j].startswith("+ "):
            base_line = d[j][2:]
            i = j + 1
        else:
            base_line = ""
            i = j
        # Classify the pair
        ref_lc = ref_line.lower()
        base_lc = (base_line or "").lower()
        is_photo = any(k in ref_lc or k in base_lc for k in PHOTOS_KEYWORDS)
        same_content = (ref_line.strip() == (base_line or "").strip())
        if is_photo:
            categories["A_PHOTOS"].append((ref_line, base_line))
        elif same_content:
            categories["B_WHITESPACE_GLYPH"].append((ref_line, base_line))
        else:
            categories["C_UNEXPLAINED"].append((ref_line, base_line))
    elif line.startswith("+ "):
        base_line = line[2:]
        ref_line = ""
        base_lc = base_line.lower()
        is_photo = any(k in base_lc for k in PHOTOS_KEYWORDS)
        same_content = ("" == base_line.strip())
        if is_photo:
            categories["A_PHOTOS"].append((ref_line, base_line))
        elif same_content:
            categories["B_WHITESPACE_GLYPH"].append((ref_line, base_line))
        else:
            categories["C_UNEXPLAINED"].append((ref_line, base_line))
        i += 1
    else:
        i += 1

print()
print("=== layout-normalised diff classification ===")
for cat, items in categories.items():
    print(f"  {cat}: {len(items)} line pair(s)")

# Also raw-stream classification (no -layout)
d_raw = diff_lines(ref_raw, base_raw)
print()
print("=== raw-stream (no -layout) line counts ===")
print(f"  reference: {len(ref_raw)} lines")
print(f"  baseline:  {len(base_raw)} lines")

cat_raw = {"A_PHOTOS": [], "B_GLYPH_OR_WRAP": [], "C_UNEXPLAINED": []}
i = 0
while i < len(d_raw):
    line = d_raw[i]
    if line.startswith("  "):
        i += 1
        continue
    if line.startswith("- "):
        ref_line = line[2:]
        j = i + 1
        while j < len(d_raw) and d_raw[j].startswith("? "):
            j += 1
        if j < len(d_raw) and d_raw[j].startswith("+ "):
            base_line = d_raw[j][2:]
            i = j + 1
        else:
            base_line = ""
            i = j
        ref_lc = ref_line.lower()
        base_lc = (base_line or "").lower()
        is_photo = any(k in ref_lc or k in base_lc for k in PHOTOS_KEYWORDS)
        same_content = (ref_line.strip() == (base_line or "").strip())
        if is_photo:
            cat_raw["A_PHOTOS"].append((ref_line, base_line))
        elif same_content:
            cat_raw["B_GLYPH_OR_WRAP"].append((ref_line, base_line))
        else:
            cat_raw["C_UNEXPLAINED"].append((ref_line, base_line))
    elif line.startswith("+ "):
        base_line = line[2:]
        base_lc = base_line.lower()
        is_photo = any(k in base_lc for k in PHOTOS_KEYWORDS)
        same_content = ("" == base_line.strip())
        if is_photo:
            cat_raw["A_PHOTOS"].append(("", base_line))
        elif same_content:
            cat_raw["B_GLYPH_OR_WRAP"].append(("", base_line))
        else:
            cat_raw["C_UNEXPLAINED"].append(("", base_line))
        i += 1
    else:
        i += 1

print()
print("=== raw-stream diff classification ===")
for cat, items in cat_raw.items():
    print(f"  {cat}: {len(items)} line pair(s)")

# Dump the unexplained ones if any
print()
print("=== UNEXPLAINED content pairs (layout) ===")
for r, b in categories["C_UNEXPLAINED"][:60]:
    print(f"  REF : {r!r}")
    print(f"  BASE: {b!r}")
    print()

print()
print("=== UNEXPLAINED content pairs (raw stream) ===")
for r, b in cat_raw["C_UNEXPLAINED"][:60]:
    print(f"  REF : {r!r}")
    print(f"  BASE: {b!r}")
    print()
