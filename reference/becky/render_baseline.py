"""D42 baseline render — calls the UNMODIFIED McLean generator with PHOTOS
neutralised and missing-italic font fallback. Produces a PDF we can compare
against the post-refactor render. This is the BEFORE half of the
byte-identical proof.
"""
import importlib.util, sys
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_orig",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_orig"] = m
spec.loader.exec_module(m)

patch_missing_italic(m)
m.PHOTOS = {k: [] for k in m.PHOTOS.keys()}
m.PHOTO_DIR = "/tmp/d42/audit/empty"

OUT = "/tmp/d42/baseline/McLean_baseline.pdf"
m.build(OUT)
print("baseline ok:", OUT)
