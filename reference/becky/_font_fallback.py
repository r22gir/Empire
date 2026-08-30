"""Helpers shared by render_baseline.py and render_after.py."""
import os
_FD = "/usr/share/fonts/truetype/dejavu/"
# Missing on this box: DejaVuSans-Oblique, DejaVuSans-BoldOblique,
# DejaVuSerif-Italic, DejaVuSerif-BoldItalic. Substitute the upright
# weight when the requested face file is absent so the script can run.
# Both BEFORE and AFTER renders get the same fallback so the byte-identical
# comparison is fair.
_FALLBACK = {
    ("SANS",  False, True):  "DejaVuSans.ttf",
    ("SANS",  True,  True):  "DejaVuSans-Bold.ttf",
    ("SERIF", False, True):  "DejaVuSerif.ttf",
    ("SERIF", True,  True):  "DejaVuSerif-Bold.ttf",
}

def patch_missing_italic(m):
    """m = loaded mclean_drapery_set_generator module."""
    new_face = {}
    for key, fname in m._FACE.items():
        path = _FD + fname
        if not os.path.exists(path):
            fam_s, bold, italic = m.SANS if key[0] == m.SANS else (m.SERIF if key[0] == m.SERIF else m.MONO), key[1], key[2]
            fam_name = "SANS" if key[0] == m.SANS else ("SERIF" if key[0] == m.SERIF else "MONO")
            sub = _FALLBACK.get((fam_name, bold, italic))
            if sub and os.path.exists(_FD + sub):
                fname = sub
        new_face[key] = fname
    m._FACE = new_face
