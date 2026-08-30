"""D42 AFTER render — calls the REFACTORED McLean generator with the same
fallback + neutralised PHOTOS as the baseline. The refactor introduced a
spec parameter and the gate_emit_client_safe function; both must be
exercised here so the comparison is apples-to-apples.

Proof of byte-identity: text-layer md5 of the after render must match the
baseline text-layer md5 in /tmp/d42/baseline/baseline_text.txt.
"""
import importlib.util, sys, hashlib
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_after",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_after"] = m
spec.loader.exec_module(m)

# Same env as the baseline.
patch_missing_italic(m)
m.SPEC_MCLEAN["photos"] = {k: [] for k in m.SPEC_MCLEAN["photos"].keys()}
m.SPEC_MCLEAN["photo_dir"] = "/tmp/d42/audit/empty"

# Render via the refactored build(spec=...) entry point.
OUT = "/tmp/d42/after/McLean_after.pdf"
m.build(OUT, spec=m.SPEC_MCLEAN, audience="client")

# Compare text layer md5 to baseline.
import subprocess
subprocess.run(["pdftotext", "-layout", OUT, "/tmp/d42/after/after_text.txt"], check=True)

with open("/tmp/d42/after/after_text.txt", "rb") as f:
    after_md5 = hashlib.md5(f.read()).hexdigest()
with open("/tmp/d42/baseline/baseline_text.txt", "rb") as f:
    base_md5 = hashlib.md5(f.read()).hexdigest()

print(f"baseline text md5: {base_md5}")
print(f"after    text md5: {after_md5}")
print(f"IDENTICAL: {base_md5 == after_md5}")
