"""Confirm gate is wired into build(): calling build() with an offending
spec + audience='client' must raise before any PDF write happens."""
import importlib.util, sys, copy, os
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_wired",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_wired"] = m
spec.loader.exec_module(m)
patch_missing_italic(m)

off = copy.deepcopy(m.SPEC_MCLEAN)
off["rooms"][0]["data"].append(
    ("INTERNAL MARKUP REGISTER", "MARKUP 50%  -  CONFIDENTIAL")
)
# Neutralise photos so the gate fail-point is unambiguous.
off["photos"] = {k: [] for k in off["photos"].keys()}
off["photo_dir"] = "/tmp/d42/audit/empty"

# This file should NEVER be written - the gate must raise first.
sentinel = "/tmp/d42/after/SHOULD_NOT_EXIST.pdf"
if os.path.exists(sentinel):
    os.remove(sentinel)

try:
    m.build(sentinel, spec=off, audience="client")
except ValueError as e:
    if os.path.exists(sentinel):
        print(f"GATE LATE - file was written before raise: {sentinel}")
        sys.exit(1)
    print(f"GATE FIRED before PDF write. Sentinel file does not exist: {sentinel!r} absent")
    print(f"  Error: {e}")
    sys.exit(0)
print("BUILD SUCCEEDED on offending spec - gate is not wired")
sys.exit(1)
